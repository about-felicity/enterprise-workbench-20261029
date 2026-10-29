"""Durable task state and strict, read-only Doubao request/answer correlation."""
import json
from pathlib import Path
import sqlite3
import time
import uuid
from urllib.parse import urlsplit


class DataError(RuntimeError):
    pass


def is_transient_error(result):
    return (result.get('status')=='complete' and result.get('finished') is True
            and result.get('native_request_confirmed') is True
            and not result.get('sources')
            and result.get('body_markdown','').strip()=='出了点问题，请稍后重试。')


class Queue:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute('pragma journal_mode=WAL')
        self.db.execute('pragma synchronous=FULL')
        self.db.executescript('''
        create table if not exists tasks(
          task_id text primary key, batch text not null, ordinal integer not null,
          question text not null, wire_question text not null unique,
          require_sources integer not null, state text not null default 'pending',
          attempts integer not null default 0, prepared_at real,
          request_id text, answer_id text, result_json text, error text,
          unique(batch,ordinal));
        create table if not exists events(
          id integer primary key, task_id text, time real not null,
          event text not null, detail text);
        ''')
        columns={r[1] for r in self.db.execute('pragma table_info(tasks)')}
        for name,definition in [('capture_retries','integer not null default 0'),('not_before','real not null default 0'),('base_wire_question','text')]:
            if name not in columns:self.db.execute('alter table tasks add column '+name+' '+definition)
        self.db.execute('update tasks set base_wire_question=wire_question where base_wire_question is null')
        self.db.execute('''create table if not exists failed_attempts(
            task_id text not null, attempt integer not null, wire_question text not null,
            request_id text, answer_id text, result_json text, reason text not null,
            archived_at real not null, primary key(task_id,attempt))''')
        self.db.commit()

    def event(self, task_id, event, detail=''):
        self.db.execute('insert into events(task_id,time,event,detail) values(?,?,?,?)',
                        (task_id,time.time(),event,detail))

    def enqueue(self, batch, questions, require_sources=False):
        if not batch or not questions or not all(isinstance(q,str) and q.strip() for q in questions):
            raise ValueError('A batch ID and non-empty question strings are required')
        with self.db:
            for ordinal, question in enumerate(questions,1):
                task_id = str(uuid.uuid5(uuid.NAMESPACE_URL, batch+':'+str(ordinal)))
                wire = question+'\n\n（采集任务编号：'+task_id+'；请仅回答上述问题。）'
                old = self.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone()
                if old:
                    if old['question'] != question or bool(old['require_sources']) != require_sources:
                        raise DataError('Existing batch cannot be changed; use a new batch ID')
                    continue
                self.db.execute('insert into tasks(task_id,batch,ordinal,question,wire_question,require_sources,base_wire_question) values(?,?,?,?,?,?,?)',
                                (task_id,batch,ordinal,question,wire,int(require_sources),wire))
                self.event(task_id,'enqueued')

    def next_task(self):
        row = self.db.execute("select * from tasks where state='prepared' order by rowid limit 1").fetchone()
        if row is None:
            row = self.db.execute("select * from tasks where state='pending' order by rowid limit 1").fetchone()
        return dict(row) if row else None

    def prepare(self, task_id, protocol=None):
        with self.db:
            changed = self.db.execute("update tasks set state='prepared',prepared_at=?,error=null where task_id=? and state='pending'",
                                      (time.time(),task_id)).rowcount
            if changed != 1:
                raise DataError('Task is not pending; sending again is forbidden')
            self.event(task_id,'send_intent_committed')
            if protocol == 'phase-v2':
                self.event(task_id, 'send_protocol_v2')

    def click_attempt(self, task_id):
        with self.db:
            row = self.db.execute('select state from tasks where task_id=?', (task_id,)).fetchone()
            if not row or row['state'] != 'prepared':
                raise DataError('Only a prepared task may attempt sending')
            boundary=self.attempt_boundary(task_id)
            if self.db.execute("select 1 from events where task_id=? and event='send_click_intent_committed' and id>?", (task_id,boundary)).fetchone():
                raise DataError('A send click was already attempted; automatic retry is forbidden')
            self.db.execute('update tasks set prepared_at=? where task_id=?', (time.time(), task_id))
            self.event(task_id, 'send_click_intent_committed')

    def may_finish_unsent(self, task_id):
        names = {r[0] for r in self.db.execute('select event from events where task_id=? and id>?', (task_id,self.attempt_boundary(task_id)))}
        # Protocol registration is committed atomically with the initial intent.
        # Legacy tasks have no such proof and must not be automatically retried.
        return 'send_protocol_v2' in names and 'send_click_intent_committed' not in names

    def attempt_boundary(self,task_id):
        return self.db.execute("select coalesce(max(id),0) from events where task_id=? and event in ('capture_retry_scheduled','operator_storage_recovery_scheduled','operator_interrupted_send_recovery_scheduled')",(task_id,)).fetchone()[0]

    def schedule_transient_retry(self,task_id,result,base_delay=90,limit=2):
        row=self.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone()
        if not row or row['state'] not in ('prepared','needs_attention'):
            raise DataError('Retry requires an unresolved current task')
        if not is_transient_error(result) or result.get('task_id')!=task_id or result.get('wire_question')!=row['wire_question']:
            raise DataError('Only the exact confirmed transient error may be retried')
        if row['request_id'] and row['request_id']!=result['request_id']:
            raise DataError('Failed request identity does not match the task')
        if row['capture_retries']>=limit:
            raise DataError('Transient error retry limit reached')
        attempt=row['capture_retries']
        retry_id=str(uuid.uuid5(uuid.UUID(task_id),'capture-retry:'+str(attempt+1)))
        wire=row['base_wire_question']+'\n（本次采集尝试编号：'+retry_id+'）'
        delay=max(30,base_delay)*(2**attempt)
        with self.db:
            self.db.execute('insert into failed_attempts values(?,?,?,?,?,?,?,?)',
                (task_id,attempt,row['wire_question'],result['request_id'],result['answer_id'],json.dumps(result,ensure_ascii=False),'confirmed_transient_error',time.time()))
            self.db.execute("update tasks set state='pending',wire_question=?,capture_retries=?,not_before=?,attempts=0,prepared_at=null,request_id=null,answer_id=null,result_json=null,error=null where task_id=?",
                (wire,attempt+1,time.time()+delay,task_id))
            self.event(task_id,'capture_retry_scheduled',json.dumps({'failed_request_id':result['request_id'],'failed_answer_id':result['answer_id'],'retry_id':retry_id,'backoff_seconds':delay}))
        return delay

    def attach_request(self, task_id, request_id):
        with self.db:
            row = self.db.execute('select request_id from tasks where task_id=?',(task_id,)).fetchone()
            if row['request_id'] and row['request_id'] != request_id:
                raise DataError('Request ID changed for the same task')
            self.db.execute('update tasks set request_id=? where task_id=?',(request_id,task_id))

    def complete(self, task_id, result):
        row = self.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone()
        if row is None or row['state'] != 'prepared':
            raise DataError('Only prepared tasks can complete')
        if result.get('task_id') != task_id or result.get('wire_question') != row['wire_question']:
            raise DataError('Result belongs to another task')
        if not result.get('finished') or not result.get('body_markdown','').strip():
            raise DataError('Incomplete or empty answer')
        if row['request_id'] and row['request_id'] != result.get('request_id'):
            raise DataError('Result request ID mismatch')
        if not result.get('request_id') or not result.get('answer_id'):
            raise DataError('Missing request/answer identity')
        if row['require_sources'] and not result.get('sources'):
            raise DataError('Required sources are missing')
        for source in result.get('sources',[]):
            url = urlsplit(source.get('url') or '')
            if not source.get('title') or url.scheme not in ('http','https') or not url.netloc:
                raise DataError('Invalid source title or URL')
        source_ids = {s.get('doc_id') for s in result.get('sources',[]) if s.get('doc_id')}
        for citation in result.get('citations',[]):
            url = urlsplit(citation.get('url') or '')
            if url.scheme not in ('http','https') or not url.netloc:
                raise DataError('Invalid citation URL')
            if citation.get('doc_id') and citation['doc_id'] not in source_ids:
                raise DataError('Citation is not linked to an extracted source')
        with self.db:
            self.db.execute("update tasks set state='completed',request_id=?,answer_id=?,result_json=?,error=null where task_id=?",
                            (result['request_id'],result['answer_id'],json.dumps(result,ensure_ascii=False),task_id))
            self.event(task_id,'completed')

    def attention(self, task_id, reason):
        with self.db:
            self.db.execute("update tasks set state='needs_attention',error=? where task_id=?",(reason,task_id))
            self.event(task_id,'needs_attention',reason)

    def retry_preparation(self, task_id, reason, limit=3):
        with self.db:
            row = self.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone()
            if row['state'] != 'pending' and not (row['state']=='prepared' and self.may_finish_unsent(task_id)):
                raise DataError('A prepared request must never be automatically resent')
            attempts = row['attempts']+1
            state = 'needs_attention' if attempts >= limit else row['state']
            self.db.execute('update tasks set attempts=?,state=?,error=? where task_id=?',(attempts,state,reason,task_id))
            self.event(task_id,'prepare_failed',reason)

    def summary(self):
        return {r[0]:r[1] for r in self.db.execute('select state,count(*) from tasks group by state')}


def parse_blocks(content):
    try:
        blocks = json.loads(content)
    except (ValueError,TypeError) as exc:
        raise DataError('Message content is not valid JSON') from exc
    if not isinstance(blocks,list) or not blocks:
        raise DataError('Message blocks must be a non-empty list')
    if any(not isinstance(b,dict) or not isinstance(b.get('content'),dict) for b in blocks):
        raise DataError('Unsupported message block schema')
    return blocks


def unpack_meta(value):
    if isinstance(value,dict):
        return value
    for _ in range(3):
        try:
            parsed = json.loads(value)
            if isinstance(parsed,dict):
                return parsed
            value = parsed
        except (ValueError,TypeError):
            if not isinstance(value,str):
                break
            value = value.replace('\\"','"').replace('\\\\','\\')
    raise DataError('Unsupported citation JSON')


def lookup(databases, task):
    matches = []
    for path in databases:
        db = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=5)
        db.row_factory = sqlite3.Row
        try:
            db.execute('pragma query_only=on')
            db.execute('begin')
            required = {'local_message_id','conversation_id','local_index','user_type','content','fts_content'}
            columns = {r[1] for r in db.execute('pragma table_info(im_message)')}
            if not required.issubset(columns):
                raise DataError('Unsupported im_message schema')
            requests = list(db.execute('select * from im_message where user_type=1 and fts_content=?',(task['wire_question'],)))
            # Newly sent messages may not yet have a full-text index. Match the
            # exact structured request instead; never infer that it was unsent.
            for candidate in db.execute("select * from im_message where user_type=1 and (fts_content is null or fts_content='') and instr(content,?)>0", (task['task_id'],)):
                blocks = parse_blocks(candidate['content'])
                text = '\n\n'.join(b['content']['text_block']['text'] for b in blocks if 'text_block' in b['content'])
                if text == task['wire_question']:
                    requests.append(candidate)
            for request in requests:
                next_user = db.execute('select min(local_index) from im_message where conversation_id=? and user_type=1 and local_index>?',
                                       (request['conversation_id'],request['local_index'])).fetchone()[0]
                end = next_user if next_user is not None else 9223372036854775807
                answers = []
                for answer in db.execute('select * from im_message where conversation_id=? and user_type=2 and local_index>? and local_index<? order by local_index',
                                         (request['conversation_id'],request['local_index'],end)):
                    blocks = parse_blocks(answer['content'])
                    if any('text_block' in b['content'] for b in blocks):
                        answers.append((answer,blocks))
                if len(answers)>1:
                    raise DataError('Multiple candidate answers; regeneration is not supported')
                confirmed=bool(request['message_id'] and request['server_index']>0) if {'message_id','server_index'}.issubset(columns) else False
                match = {'status':'waiting','request_id':request['local_message_id'],'native_request_confirmed':confirmed}
                if answers:
                    answer, blocks = answers[0]
                    if all(b.get('is_finish') is True for b in blocks):
                        body, sources, citations, queries = [], [], [], []
                        for block in blocks:
                            content = block['content']
                            if content.get('pc_event_block') not in (None,''):
                                raise DataError('Unsupported non-empty PC event metadata')
                            if not set(content).issubset({'text_block','search_query_result_block','pc_event_block'}):
                                raise DataError('Unsupported answer block type')
                            if 'text_block' in content:
                                text = content['text_block'].get('text')
                                if not isinstance(text,str):
                                    raise DataError('Invalid answer text')
                                body.append(text)
                            search = content.get('search_query_result_block',{})
                            queries.extend(search.get('queries',[]))
                            for item in search.get('results',[]):
                                if not isinstance(item.get('text_card'),dict):
                                    raise DataError('Unsupported search result type')
                                card = item['text_card']
                                sources.append({k:card.get(k) for k in ['index','title','url','doc_id']})
                            for meta in block.get('meta_info',[]):
                                info = unpack_meta(meta.get('info',''))
                                if info.get('url'):
                                    citations.append({k:info.get(k) for k in ['pos','title','url','doc_id','insert_text','summary']})
                        match.update(status='complete',task_id=task['task_id'],wire_question=task['wire_question'],
                                     request_id=request['local_message_id'],answer_id=answer['local_message_id'],
                                     conversation_id=request['conversation_id'],finished=True,
                                     body_markdown='\n\n'.join(body),sources=sources,citations=citations,search_queries=queries)
                matches.append(match)
        finally:
            db.close()
    if len(matches)>1:
        raise DataError('Duplicate submitted requests for the same task')
    return matches[0] if matches else {'status':'absent'}

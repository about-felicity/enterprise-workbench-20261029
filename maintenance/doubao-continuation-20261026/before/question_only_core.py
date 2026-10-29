"""Local task identities and native bindings; the transmitted prompt is only the question."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import time
import uuid

from unattended_core import Queue as LegacyQueue, DataError, parse_blocks, unpack_meta, is_transient_error

PROTOCOL='question-only-v1'

def native_tip(block):
    tip=block.get('content',{}).get('tips_block')
    if (block.get('block_type')!=10053 or not isinstance(tip,dict)
        or set(tip)!={'text','type'} or type(tip['type']) is not int or tip['type']!=1
        or not isinstance(tip['text'],str) or not tip['text'].strip()):
        raise DataError('Unsupported native tips block; completeness unproven')
    return tip


def source_absence_verified(result):
    """A finished native answer can provide no web citations (e.g. commerce cards)."""
    blocks=result.get('raw_answer_blocks')
    if (result.get('status')!='complete' or result.get('finished') is not True
        or result.get('native_request_confirmed') is not True
        or not (result.get('first_user_turn') is True or permission_continuation_verified(result)) or result.get('prompt_protocol')!=PROTOCOL
        or result.get('body_capture_complete') is not True or result.get('source_capture_complete') is not True
        or result.get('sources') or result.get('citations') or result.get('search_queries')
        or result.get('source_availability')!='not_provided'
        or result.get('native_answer_status')!=21 or not isinstance(blocks,list) or not blocks):return False
    for block in blocks:
        content=block.get('content',{})
        if block.get('is_finish') is not True or 'search_query_result_block' in content:return False
        if not set(content).issubset({'pc_event_block','text_block','tips_block'}) or content.get('pc_event_block'):return False
        if 'tips_block' in content:
            try:native_tip(block)
            except DataError:return False
        for meta in block.get('meta_info',[]):
            if unpack_meta(meta.get('info','')).get('url'):return False
    parts=[]
    for b in blocks:
        if 'tips_block' in b['content']:parts.append(native_tip(b)['text'])
        if 'text_block' in b['content']:parts.append(b['content']['text_block']['text'])
    text='\n\n'.join(parts)
    return bool(text.strip()) and text==result.get('body_markdown')


def permission_card(blocks):
    if len(blocks)!=1 or blocks[0].get('block_type')!=10066 or blocks[0].get('is_finish') is not True:return False
    content=blocks[0].get('content',{})
    if set(content)!={'permission_apply_block'}:return False
    try:data=json.loads(content['permission_apply_block']['permission_data'])
    except (KeyError,TypeError,ValueError):return False
    grants=data.get('grantingList',[])
    return (data.get('doubaoAppletName')=='抖音商城' and data.get('refuseInteractReplay') is True
            and len(grants)==1 and grants[0].get('grantingName')=='aweme_login' and grants[0].get('permissionStatus')=='pending')


def permission_continuation_verified(result):
    p=result.get('permission_continuation',{})
    return bool(p.get('declined_at') and p.get('original_request_id')==result.get('request_id')
        and p.get('continuation_request_id') and p['continuation_request_id']!=p['original_request_id']
        and p.get('original_first_user_turn') is True and p.get('prompt')==result.get('wire_question')
        and permission_card(p.get('original_permission_blocks',[])))


class Queue(LegacyQueue):
    source_absence_verified=staticmethod(source_absence_verified)

    def __init__(self,path):
        path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(path)) as db:
            exists=db.execute("select 1 from sqlite_master where type='table' and name='tasks'").fetchone()
            if exists:
                marker=db.execute("select 1 from sqlite_master where type='table' and name='prompt_protocol'").fetchone()
                if not marker or db.execute('select value from prompt_protocol').fetchone()[0]!=PROTOCOL:
                    raise DataError('Legacy task database cannot be converted in place')
            else:
                db.executescript('''
                create table tasks(task_id text primary key,batch text not null,ordinal integer not null,
                  question text not null,wire_question text not null,require_sources integer not null,
                  state text not null default 'pending',attempts integer not null default 0,prepared_at real,
                  request_id text,answer_id text,result_json text,error text,unique(batch,ordinal));
                create table prompt_protocol(value text not null);
                ''')
                db.execute('insert into prompt_protocol values(?)',(PROTOCOL,));db.commit()
        super().__init__(path)

    def complete_nontext(self,task_id,result):
        row=self.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone()
        if not row or row['state'] not in {'prepared','needs_attention'}:
            raise DataError('Non-text observation requires the original unresolved task')
        if (result.get('status')!='nontext_complete' or result.get('native_answer_kind')!='video_only'
            or result.get('task_id')!=task_id or result.get('wire_question')!=row['question']
            or result.get('finished') is not True or result.get('native_request_confirmed') is not True
            or result.get('rich_media_capture_complete') is not True or not result.get('rich_cards')
            or result.get('text_body_present') is not False or result.get('body_capture_complete') is not False
            or result.get('first_user_turn') is not True or result.get('prompt_protocol')!=PROTOCOL
            or not result.get('request_id') or not result.get('answer_id')
            or (row['request_id'] and row['request_id']!=result['request_id'])):
            raise DataError('Non-text classification identity/completion proof failed')
        with self.db:
            self.db.execute("update tasks set state='completed_nontext',request_id=?,answer_id=?,result_json=?,error=null where task_id=?",
                (result['request_id'],result['answer_id'],json.dumps(result,ensure_ascii=False),task_id))
            self.event(task_id,'completed_nontext','native_video_only_answer; no model resend; excluded from text analysis')

    def enqueue(self,batch,questions,require_sources=False):
        if not batch or not questions or not all(isinstance(q,str) and q and q==q.strip() for q in questions):
            raise ValueError('Exact nonempty question strings required')
        with self.db:
            for ordinal,question in enumerate(questions,1):
                task_id=str(uuid.uuid5(uuid.NAMESPACE_URL,batch+':'+str(ordinal)))
                old=self.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone()
                if old:
                    if old['question']!=question or old['wire_question']!=question or bool(old['require_sources'])!=require_sources:
                        raise DataError('Immutable question-only task changed')
                    continue
                self.db.execute('insert into tasks(task_id,batch,ordinal,question,wire_question,require_sources,base_wire_question) values(?,?,?,?,?,?,?)',
                                (task_id,batch,ordinal,question,question,int(require_sources),question))
                self.event(task_id,'enqueued',PROTOCOL)

    def schedule_transient_retry(self,task_id,result,base_delay=90,limit=2):
        row=self.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone()
        if not row or row['state'] not in ('prepared','needs_attention') or not is_transient_error(result):
            raise DataError('Only a proven completed transient answer may be retried')
        if result.get('task_id')!=task_id or result.get('wire_question')!=row['question'] or (limit is not None and row['capture_retries']>=limit):
            raise DataError('Transient retry identity or limit mismatch')
        if row['request_id'] and row['request_id']!=result['request_id']:raise DataError('Native request changed')
        delay=min(900,max(30,base_delay)*2**min(row['capture_retries'],4))
        with self.db:
            self.db.execute('insert into failed_attempts values(?,?,?,?,?,?,?,?)',
                (task_id,row['capture_retries'],row['wire_question'],result['request_id'],result['answer_id'],json.dumps(result,ensure_ascii=False),'confirmed_transient_error',time.time()))
            self.db.execute("update tasks set state='pending',capture_retries=capture_retries+1,not_before=?,attempts=0,prepared_at=null,request_id=null,answer_id=null,result_json=null,error=null where task_id=?",(time.time()+delay,task_id))
            self.event(task_id,'capture_retry_scheduled',json.dumps({'request_id':result['request_id'],'delay':delay,'prompt_unchanged':True}))
        return delay


def request_fingerprint(row):
    """SQLite rowid changes on native history replacement; message identity does not."""
    return {**{k:row[k] for k in ('local_message_id','conversation_id','local_index','message_id','server_index')},
            'prompt_sha256':hashlib.sha256(message_text(row).encode('utf-8')).hexdigest()}


def baseline(databases,question=None):
    started=time.time()
    values=[]
    for path in databases:
        path=Path(path).resolve()
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            db.execute('begin')
            columns={r[1] for r in db.execute('pragma table_info(im_message)')}
            if not {'local_message_id','conversation_id','user_type','content','local_index'}.issubset(columns):
                raise DataError('Native message schema changed')
            requests=[]
            for row in db.execute('select * from im_message where user_type=1'):
                try:
                    if question is None or message_text(row)==question:requests.append(request_fingerprint(row))
                except DataError:
                    # Unrelated unsupported historical input cannot prove an identity.
                    continue
            values.append({'database':str(path),'max_rowid':db.execute('select coalesce(max(rowid),0) from im_message').fetchone()[0],
                           'conversations':[r[0] for r in db.execute('select distinct conversation_id from im_message')],
                           'prior_requests':requests})
    return {'created_at':started,'databases':values,'protocol':PROTOCOL}


def message_text(row):
    return '\n\n'.join(b['content']['text_block']['text'] for b in parse_blocks(row['content']) if 'text_block' in b['content'])


def correlate(snapshot,question):
    candidates=[]
    for item in snapshot['databases']:
        with closing(sqlite3.connect(Path(item['database']).as_uri()+'?mode=ro',uri=True)) as db:
            db.row_factory=sqlite3.Row
            for row in db.execute('select * from im_message where rowid>? and user_type=1 order by rowid',(item['max_rowid'],)):
                if message_text(row)!=question:continue
                # The App replaces its temporary local conversation ID after
                # acknowledgement. Bind only the confirmed native identity.
                if not row['message_id'] or row['server_index']<=0 or str(row['conversation_id']).endswith('-local'):continue
                if row['conversation_id'] in item['conversations']:
                    # History hydration may replace an old row above max_rowid.
                    # Ignore only an exact identity already observed before this send.
                    if request_fingerprint(row) in item.get('prior_requests',[]):continue
                    raise DataError('Question was sent in an existing conversation')
                if db.execute('select count(*) from im_message where conversation_id=? and user_type=1 and local_index<?',
                              (row['conversation_id'],row['local_index'])).fetchone()[0]:
                    raise DataError('Question is not the first turn')
                candidates.append({'database':item['database'],'conversation_id':row['conversation_id'],
                                   'request_id':row['local_message_id'],'prompt':question,'protocol':PROTOCOL})
    if len(candidates)>1:raise DataError('Multiple new native requests; automatic resend forbidden')
    return candidates[0] if candidates else None


def canonical_binding(task,binding,snapshot):
    with closing(sqlite3.connect(Path(binding['database']).as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        row=db.execute('select * from im_message where user_type=1 and local_message_id=?',(binding['request_id'],)).fetchone()
        if not row or row['conversation_id']==binding['conversation_id']:return binding
        if (not str(binding['conversation_id']).endswith('-local') or not str(row['conversation_id']).isdigit()
                or not row['message_id'] or row['server_index']<=0 or message_text(row)!=task['question']):
            raise DataError('Unproven native conversation identity change')
        old=next(v for v in snapshot['databases'] if v['database']==binding['database'])
        if row['conversation_id'] in old['conversations']:raise DataError('Promoted conversation was not fresh')
        if db.execute('select count(*) from im_message where conversation_id=? and user_type=1',(row['conversation_id'],)).fetchone()[0]!=1:
            raise DataError('Promoted conversation contains multiple user turns')
        return {**binding,'conversation_id':row['conversation_id'],'previous_local_conversation_id':binding['conversation_id'],
                'server_acknowledged_at':time.time()}


def lookup_bound(task,binding):
    with closing(sqlite3.connect(Path(binding['database']).as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row;db.execute('begin')
        request=db.execute('select * from im_message where user_type=1 and local_message_id=? and conversation_id=?',
                           (binding['request_id'],binding['conversation_id'])).fetchone()
        if not request:return {'status':'awaiting_native_history'}
        if task['wire_question']!=task['question'] or message_text(request)!=task['question']:
            raise DataError('Native question differs from the exact original question')
        users=db.execute('select * from im_message where conversation_id=? and user_type=1 order by local_index',(binding['conversation_id'],)).fetchall()
        continuation=None;original_request=request
        if len(users)!=1:
            if (len(users)!=2 or request['server_index']!=1 or users[0]['local_message_id']!=request['local_message_id'] or not binding.get('optional_commerce_declined_at')
                    or message_text(users[1])!=task['question'] or users[1]['server_index']<=request['server_index']):raise DataError('Native conversation contains another user turn')
            permission_answers=db.execute('select * from im_message where conversation_id=? and user_type=2 and local_index>? and local_index<? order by local_index',
                (binding['conversation_id'],request['local_index'],users[1]['local_index'])).fetchall()
            if len(permission_answers)!=1 or permission_answers[0]['status']!=21 or not permission_card(parse_blocks(permission_answers[0]['content'])):raise DataError('Native conversation contains another user turn')
            continuation={'original_request_id':request['local_message_id'],'continuation_request_id':users[1]['local_message_id'],
                'original_first_user_turn':True,'prompt':task['question'],'declined_at':binding['optional_commerce_declined_at'],
                'original_permission_blocks':parse_blocks(permission_answers[0]['content']),'continuation_question_blocks':parse_blocks(users[1]['content']),
                'continuation_server_index':users[1]['server_index'],'kind':'native_optional_permission_replay'}
            request=users[1]
        answers=[]
        for answer in db.execute('select * from im_message where conversation_id=? and user_type=2 and local_index>? order by local_index',
                                 (binding['conversation_id'],request['local_index'])):
            blocks=parse_blocks(answer['content'])
            if any('text_block' in b['content'] for b in blocks):answers.append((answer,blocks))
        if len(answers)>1:raise DataError('Multiple native answers; regeneration unsupported')
        columns=set(request.keys())
        confirmed=bool(request['message_id'] and request['server_index']>0) if {'message_id','server_index'}.issubset(columns) else False
        result={'status':'waiting','request_id':original_request['local_message_id'],'native_request_confirmed':confirmed}
        if not answers:return result
        answer,blocks=answers[0]
        if not all(b.get('is_finish') is True for b in blocks):return result
        body=[];sources=[];citations=[];queries=[];tips=[]
        for block in blocks:
            content=block['content']
            if content.get('pc_event_block') not in (None,'') or not set(content).issubset({'pc_event_block','text_block','search_query_result_block','tips_block'}):
                raise DataError('Unknown answer block; completeness unproven: '+','.join(sorted(content)))
            if 'tips_block' in content:
                tip=native_tip(block)
                # This is visible App-owned answer text, not a source, error,
                # or instruction. Keep every character and the original block.
                body.append(tip['text']);tips.append(tip)
            if 'text_block' in content:
                text=content['text_block'].get('text')
                if not isinstance(text,str):raise DataError('Invalid text block')
                body.append(text)
            search=content.get('search_query_result_block',{});queries.extend(search.get('queries',[]))
            for item in search.get('results',[]):
                card=item.get('text_card')
                if not isinstance(card,dict):raise DataError('Unsupported source card')
                sources.append({**{k:card.get(k) for k in ('index','title','url','doc_id')},'native_source':card})
            for meta in block.get('meta_info',[]):
                info=unpack_meta(meta.get('info',''))
                if info.get('url'):citations.append({k:info.get(k) for k in ('pos','title','url','doc_id','insert_text','summary')})
        result.update(status='complete',finished=True,task_id=task['task_id'],wire_question=task['question'],
                      question_id=original_request['local_message_id'],answer_id=answer['local_message_id'],
                      conversation_id=binding['conversation_id'],body_markdown='\n\n'.join(body),body_parts=body,
                      sources=sources,citations=citations,search_queries=queries,
                      raw_answer_blocks=blocks,raw_question_blocks=parse_blocks(original_request['content']),
                      capture_mode='android_app_sqlite_question_only',prompt_protocol=PROTOCOL,
                      first_user_turn=continuation is None,body_capture_complete=True,source_capture_complete=True)
        if continuation:result['permission_continuation']=continuation
        result['native_answer_status']=answer['status'] if 'status' in answer.keys() else None
        if tips:result['native_tips']=tips
        if not sources and not citations and not queries and not any('search_query_result_block' in b['content'] for b in blocks):
            result['source_availability']='not_provided'
        return result

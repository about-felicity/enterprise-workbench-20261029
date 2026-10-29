"""Read App-owned WCDB through SQLite's transactional WAL reader; no network sends."""
from contextlib import closing
import hashlib,json,sqlite3,time
from pathlib import Path
import sys
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import DataError
from unattended_worker import atomic_json
from device import CONTAINER

DATABASES=Path('/var/lib/docker/volumes/'+CONTAINER+'-data/_data/data/com.deepseek.chat/databases')

def connect(path):
 db=sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=5)
 db.row_factory=sqlite3.Row;db.execute('pragma query_only=on');db.execute('begin');return db

def sessions():
 result=[]
 for path in DATABASES.rglob('*.db'):
  if path.is_symlink():continue
  with closing(connect(path)) as db:
   for row in db.execute("select name from sqlite_master where type='table' and name like 'chat_session_messages_%'"):
    table=row['name'];columns={r['name'] for r in db.execute('pragma table_info('+quote(table)+')')}
    if not {'message_id','parent_id','role','status','inserted_at','fragments'}<=columns:raise DataError('DeepSeek App database schema changed')
    messages=[dict(r) for r in db.execute('select * from '+quote(table)+' order by message_id')]
    result.append({'database':str(path),'table':table,'messages':messages})
 return result

def quote(value):return '"'+value.replace('"','""')+'"'

def fragments(message):
 value=message['fragments']
 if isinstance(value,bytes):value=value.decode('utf8')
 value=json.loads(value)
 if not isinstance(value,list) or not all(isinstance(v,dict) for v in value):raise DataError('Unknown DeepSeek App fragment encoding')
 return value

def question(message):
 values=fragments(message)
 if len(values)!=1 or values[0].get('type')!='REQUEST':return None
 return values[0].get('content')

def parse(task,session):
 messages=session['messages'];users=[m for m in messages if m['role']=='USER']
 if len(users)!=1 or question(users[0])!=task['question']:raise DataError('DeepSeek exact first-turn identity failed')
 user=users[0];answers=[m for m in messages if m['role']=='ASSISTANT' and m['parent_id']==user['message_id']]
 if len(answers)>1:raise DataError('Multiple DeepSeek answers for one question')
 cid=session['table'].removeprefix('chat_session_messages_')
 request=cid+':'+str(user['message_id'])
 result={'status':'pending','request_id':request,'native_request_confirmed':True,'phase':'generating'}
 if not answers or answers[0]['status']!='FINISHED':return result
 answer=answers[0];parts=fragments(answer);body=[];sources=[];citations=[];queries=[]
 if answer.get('thinking_enabled') not in (False,0):raise DataError('DeepSeek native answer has thinking enabled or unverified')
 for part in parts:
  kind=part.get('type')
  if kind=='RESPONSE':
   if not isinstance(part.get('content'),str):raise DataError('Response fragment has no text')
   body.append(part['content']);citations.extend(part.get('references') or [])
  elif kind=='SEARCH':
   if part.get('status')!='FINISHED':return result
   values=part.get('results')
   if not isinstance(values,list):raise DataError('Missing native search result list')
   for value in values:
    if not isinstance(value,dict):raise DataError('Invalid native source entry')
    title,url=value.get('title'),value.get('url')
    from urllib.parse import urlsplit
    if not isinstance(url,str):raise DataError('Missing native source URL')
    parsed=urlsplit(url)
    if parsed.scheme not in {'http','https'} or not parsed.hostname:raise DataError('Invalid native source URL')
    if title is not None and not isinstance(title,str):raise DataError('Invalid native source title type')
    if not title or not title.strip():
     # Use the real URL as a display label; never invent an article title or
     # drop an otherwise complete native search result. Raw fragments stay intact.
     sources.append({**value,'title':url,'url':url,'native_title':title,
                     'native_title_missing':True,'title_origin':'url_fallback'})
    else:sources.append({**value,'title':title,'url':url})
   queries.extend(part.get('queries') or [])
  elif kind=='THINK':
   if part.get('content'):raise DataError('Unexpected DeepSeek thinking fragment')
  elif kind=='TIP':continue
  else:raise DataError('Unverified native fragment type')
 if not body or not ''.join(body).strip() or not sources:return {**result,'phase':'awaiting_complete_snapshot','reason':'body_or_search_sources_pending'}
 result.update(status='complete',finished=True,task_id=task['task_id'],wire_question=task['question'],
  answer_id=cid+':'+str(answer['message_id']),conversation_id=cid,body_markdown='\n\n'.join(body),body_parts=body,
  sources=sources,citations=citations,search_queries=queries,raw_answer_blocks=parts,raw_question_blocks=fragments(user),
  capture_mode='android_app_wcdb_question_only',prompt_protocol='question-only-v1',first_user_turn=True,
  body_capture_complete=True,source_capture_complete=True,thinking_enabled=False,search_enabled=True)
 if any(s.get('native_title_missing') for s in sources):
  result.update(source_metadata_complete=False,source_title_missing_count=sum(bool(s.get('native_title_missing')) for s in sources))
 return result

class Reader:
 def __init__(self,root):self.root=Path(root);(self.root/'bindings').mkdir(exist_ok=True,mode=0o700)
 def close(self):pass
 def before_new_chat(self,task):
  path=self.root/'bindings'/(task['task_id']+'.baseline.json')
  # A failed unsent preparation may be retried; never replace a clicked baseline.
  if not path.exists():atomic_json(path,{'at':time.time(),'sessions':[s['table'] for s in sessions()]})
 def lookup(self,task):
  path=self.root/'bindings'/(task['task_id']+'.json');baseline=self.root/'bindings'/(task['task_id']+'.baseline.json')
  if not baseline.exists():return {'status':'absent'}
  before=json.loads(baseline.read_text());bound=json.loads(path.read_text()) if path.exists() else None
  matches=[]
  for session in sessions():
   if bound:
    if session['database']!=bound['database'] or session['table']!=bound['table']:continue
   elif session['table'] in before['sessions']:continue
   users=[m for m in session['messages'] if m['role']=='USER']
   if not users:continue
   if question(users[0])!=task['question']:continue
   if not bound and float(users[0]['inserted_at'])<before['at']-2:continue
   matches.append(session)
  if len(matches)>1:raise DataError('Ambiguous DeepSeek native request')
  if not matches:return {'status':'pending' if bound else 'absent'}
  session=matches[0]
  if not bound:atomic_json(path,{'database':session['database'],'table':session['table'],'task_id':task['task_id']})
  result=parse(task,session)
  if result['status']=='complete':atomic_json(self.root/'bindings'/(task['task_id']+'.native.json'),session)
  return result

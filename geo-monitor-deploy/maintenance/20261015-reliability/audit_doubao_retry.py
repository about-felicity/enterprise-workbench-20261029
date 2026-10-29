"""Read-only proof for original failed attempts and later captures; no model actions."""
import json, sqlite3, time, sys, hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-capture','/home/user/redroid-doubao/geo-batch-code']
from native_soak import read, atomic
from question_only_core import lookup_bound
base=Path('/opt/monitor/geo-capture')
p=read(base/'soak12h_current.json'); m=read(Path(p['root'])/'manifest.json')
home=Path('/home/user/redroid-doubao/batches')/m['jobs']['doubao1']['batch']
out=base/'maintenance/20261015-reliability/doubao1-transient-retry';out.mkdir(exist_ok=True,mode=0o700)
report={'at':time.time(),'test_id':p['test_id'],'model_actions':0,'attempts':[]}
with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 backup=out/('tasks-snapshot-'+str(time.time_ns())+'.sqlite')
 with sqlite3.connect(backup) as dest: db.backup(dest)
 for row in db.execute('select * from failed_attempts order by archived_at'):
  f=dict(row); task=dict(db.execute('select * from tasks where task_id=?',(f['task_id'],)).fetchone())
  result=json.loads(f['result_json']); events=[dict(e) for e in db.execute('select time,event,detail from events where task_id=? order by time',(f['task_id'],))]
  entry={'task_id':f['task_id'],'ordinal':task['ordinal'],'question':task['question'],'failed_attempt':{k:v for k,v in f.items() if k!='result_json'},'original_proof':{k:result.get(k) for k in ('status','finished','native_request_confirmed','first_user_turn','request_id','answer_id','body_markdown','sources','wire_question')},'events':events,'current_state':task['state'],'capture_retries':task['capture_retries']}
  for attempt in range(task['capture_retries']+1):
   binding_path=home/(task['task_id']+'-attempt-'+str(attempt)+'.binding.json')
   if not binding_path.exists():continue
   binding=read(binding_path); oldtask={**task,'request_id':binding.get('request_id'),'capture_retries':attempt}
   observed=lookup_bound(oldtask,binding)
   atomic(out/('original-'+str(task['ordinal'])+'-attempt-'+str(attempt)+'.json'),observed)
   entry.setdefault('native_reads',[]).append({'attempt':attempt,'binding':{k:binding.get(k) for k in ('conversation_id','request_id','answer_id')},'observed':{k:observed.get(k) for k in ('status','finished','native_request_confirmed','first_user_turn','request_id','answer_id')},'body_characters':len(observed.get('body_markdown','')),'body_sha256':hashlib.sha256(observed.get('body_markdown','').encode()).hexdigest(),'source_count':len(observed.get('sources',[]))})
  if task['result_json']:
   r=json.loads(task['result_json']);entry['current_result']={k:r.get(k) for k in ('status','finished','native_request_confirmed','first_user_turn','request_id','answer_id')};entry['current_body_characters']=len(r.get('body_markdown',''));entry['current_sources']=len(r.get('sources',[]))
  report['attempts'].append(entry)
atomic(out/'audit.json',report)
export=Path('/tmp/geo-reliability-export/doubao1-transient-retry-audit.json');atomic(export,report);export.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))

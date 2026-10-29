"""One creation-only browser observation; never calls a GEO ingestion receiver."""
import argparse,fcntl,hashlib,json,signal,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from browser_backend import ROOT,read,atomic,command,probe
from geo_source_cards.journal import Journal
STOP=False
def stop(*_):
 global STOP
 STOP=True

def assignment_id(lane,task_id):
 return hashlib.sha256((str(Path(lane).resolve())+'\n'+task_id).encode()).hexdigest()

def record(value,task):
 if value.get('prompt')!=task['question'] or value.get('status')!='success' or not value.get('web_body','').strip() or value.get('source_capture_complete') is not True or len(value.get('sources',[]))<int(value.get('expected_source_count',0)):
  raise ValueError('Private browser answer is not complete')
 return {'model':'deepseek','question':task['question'],'task_id':task['task_id'],'round':task['round'],
         'body':value['web_body'],'sources':value['sources'],'source_capture_complete':True,'body_capture_complete':True,
         'capture_mode':'deepseek_browser_extension','captured_at':value['finished_at'],'url':value.get('conversation_url') or value.get('url',''),
         'browser_run_id':value['run_id'],'scope':'creation_only'}

def run(lane,batch,rounds):
 lane=Path(lane).resolve();base=Path('/opt/monitor/geo-content').resolve()
 if base not in lane.parents or lane.is_symlink():raise ValueError('Private creation directory required')
 root=lane/'collector';root.mkdir(parents=True,exist_ok=True)
 output=lane/'results.jsonl';journal=Journal(root/'tasks.sqlite')
 questions=[q.strip() for q in (lane/'questions.txt').read_text().splitlines() if q.strip()]
 tasks=journal.plan(batch,'deepseek',questions,rounds,output)
 task=next((dict(t) for t in tasks if t['state']!='completed'),None)
 if not task:return 0
 private_id=assignment_id(lane,task['task_id'])
 assignment={'batch':'creation-private-'+private_id,'questions':[task['question']],'rounds':1}
 # The production adapter holds this same lock for its entire active job.
 with (ROOT/'assignment.lock').open('a') as lock:
  try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except BlockingIOError:return 75
  if probe()['status']!='ready':return 77
  state=read(ROOT/'state.json');job=state.get('plugin_job') or {};current=state.get('assignment') or {}
  if job.get('state') in ('running','paused') and current.get('batch')!=assignment['batch']:return 75
  if task['state']=='pending':journal.start(task['task_id'],submission=True)
  key=hashlib.sha256(('creation-browser:'+private_id).encode()).hexdigest()[:32]
  started=command('start',assignment,key=key);run_id=started['job']['id']
  current_state=read(ROOT/'state.json');current_job=current_state.get('plugin_job') or {}
  if current_state.get('assignment',{}).get('batch')==assignment['batch'] and current_job.get('state')=='paused' and (current_job.get('inFlight') or {}).get('phase')!='send_intent':
   command('resume',assignment)
  atomic(root/(task['task_id']+'.browser.json'),{'assignment':assignment,'run_id':run_id})
  while True:
   found=[]
   path=ROOT/'data/deepseek_results.jsonl'
   if path.exists():
    found=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
   value=next((v for v in found if v.get('run_id')==run_id),None)
   if value:
    result=record(value,task)
    with journal.db:
     journal.db.execute("update captures set state='completed',finished=?,result=?,error=null where task_id=? and state in ('capturing','needs_attention')",(time.time(),json.dumps(result,ensure_ascii=False),task['task_id']))
     journal.db.execute('insert into automatic_recovery_events(task_id,event,details,epoch) values(?,?,?,?)',(task['task_id'],'private_browser_result_verified',run_id,time.time()))
    journal.export(output);return 0
   state=read(ROOT/'state.json');job=state.get('plugin_job') or {};flight=job.get('inFlight') or {};phase=flight.get('phase')
   if phase in ('submitted','send_intent'):
    intent=journal.db.execute('select attempted from capture_submissions where task_id=?',(task['task_id'],)).fetchone()
    if intent and not intent[0]:journal.submission(task['task_id'],{'url':flight.get('conversationUrl','')},attempted=True)
   if probe()['status'] in ('login_required','risk_blocked','verification_required'):return 77
   if STOP and phase not in ('submitted','send_intent'):
    command('pause',assignment);return 0
   if job.get('state')=='paused':
    atomic(lane.parent/'blocked-deepseek.json',{'at':time.time(),'kind':'unknown_execution','message':'浏览器发送或采集结果需要核对，保留原会话；不会重发未知问题'})
    return 2
   time.sleep(3)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--lane',required=True);p.add_argument('--batch',required=True);p.add_argument('--rounds',type=int,required=True);a=p.parse_args()
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
 raise SystemExit(run(a.lane,a.batch,a.rounds))

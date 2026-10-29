"""Bounded same-session verification rechecks for GEO and creation collectors."""
import json,os,pwd,sqlite3,subprocess,time,signal
from contextlib import closing,contextmanager
from pathlib import Path
from geo_source_cards.runtime import atomic_json,process_lock

GEO=Path('/opt/monitor/geo-capture');STUDIO=Path('/opt/monitor/geo-content/studio')
DELAYS=(900,1800,3600);LIMIT=3
@contextmanager
def browser_lock(path,wait=0):
 import fcntl
 with path.open('a+b') as stream:
  deadline=time.monotonic()+wait
  while True:
   try:fcntl.flock(stream,fcntl.LOCK_EX|fcntl.LOCK_NB);break
   except BlockingIOError:
    if time.monotonic()>=deadline:raise RuntimeError('Another collector uses browser')
    time.sleep(1)
  try:yield
  finally:fcntl.flock(stream,fcntl.LOCK_UN)
def read(p):
 try:return json.loads(p.read_text())
 except FileNotFoundError:return {}
def due(state,now):
 return state.get('attempts',0)<LIMIT and now>=state.get('next_at',0)
def failed(state,now,status):
 n=state.get('attempts',0)+1
 return {'attempts':n,'next_at':now+DELAYS[min(n-1,2)],'status':status if n<LIMIT else 'needs_attention','last_status':status,'at':now}
def candidates():
 manifests=[]
 for p in (GEO/'batches').glob('*/manifest.json'):
  v=read(p)
  if v.get('model')=='wenxin_card':manifests.append((v.get('created_at',0),p.parent))
 if manifests:
  root=max(manifests)[1]
  if read(root/'bridge_health.json').get('status')=='waiting_verification' and not (root/'pause.json').exists():
   yield {'name':'GEO文心','runtimes':[root/'collector'],'blocks':[],'lock':GEO/'search_browser.lock','state':GEO/'profiles/search/wenxin_card/verification_retry.json','service':'geo-web@'+root.name+'.service','pause':root/'pause.json','settings':None}
 for root in (STUDIO/'capture').glob('plan-*'):
  cfg=read(root/'settings.json');plan=read(STUDIO/'plans'/(root.name+'.json'))
  if not cfg.get('enabled') or cfg.get('paused') or plan.get('deleted_at') or not plan.get('enabled'):continue
  blocks=[p for p in root.glob('days/*/blocked-wenxin_card.json') if p.parent.name!=cfg.get('paused_day')]
  if not blocks:continue
  runtimes=[p.parent/'wenxin_card/collector' for p in blocks]
  # A new day may inherit a block before a journal has been created.
  if not any((p/'tasks.sqlite').exists() for p in runtimes):runtimes+=list(root.glob('days/*/wenxin_card/collector'))
  yield {'name':plan.get('name',root.name),'runtimes':runtimes,'blocks':blocks,'lock':root/'profiles/search/wenxin_card/browser.lock','state':root/'profiles/search/wenxin_card/verification_retry.json','service':None,'pause':root/'pause.json','settings':root/'settings.json'}
def paused(item):
 if item['pause'].exists():return True
 cfg=read(item['settings']) if item['settings'] else {}
 return bool(cfg.get('paused') or (item['settings'] and not cfg.get('enabled')))
def probe_target(item):
 for root in sorted(item['runtimes'],reverse=True):
  dbpath=root/'tasks.sqlite'
  if not dbpath.exists():continue
  with closing(sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True)) as db:
   row=db.execute("select question from captures where model='wenxin_card' and state in ('pending','needs_attention','failed_deferred') order by rowid limit 1").fetchone()
   if row:return root,row[0]
 return None
def clear_verified(item,proof):
 assert proof.get('status')=='ready' and time.time()-proof['at']<300
 if paused(item):return False
 owner=pwd.getpwnam('user')
 for root in item['runtimes']:
  path=root/'tasks.sqlite'
  if not path.exists():continue
  with closing(sqlite3.connect(path)) as db:
   if not db.execute("select 1 from sqlite_master where name='search_recovery_control'").fetchone():continue
   with db:db.execute('update search_recovery_control set streak=0,cooldown_until=0,blocked=0 where id=1')
  state=root/'search_recovery.json';old=read(state)
  atomic_json(state,{**old,'streak':0,'cooldown_until':0,'blocked':0,'status':'ready','checked_epoch':time.time(),'verification_probe':proof})
  os.chown(state,owner.pw_uid,owner.pw_gid)
 for path in item['blocks']:path.unlink(missing_ok=True)
 return True
def run():
 results=[]
 for item in candidates():
  state=read(item['state']);now=time.time()
  if not due(state,now):
   results.append({'name':item['name'],**state});continue
  target=probe_target(item)
  if not target:continue
  root,question=target
  try:
   with browser_lock(item['lock'],wait=90 if item['service'] else 0):
    if paused(item):continue
    # Reserve attempt before launch: a process crash cannot cause an endless loop.
    reserved=failed(state,now,'checking');atomic_json(item['state'],reserved)
    cmd=['/usr/sbin/runuser','-u','user','--',str(GEO/'venv/bin/python'),str(GEO/'wenxin_readiness_probe.py'),'--runtime',str(root),'--question',question]
    try:
     cached=max([read(r/'verification_probe_latest.json') for r in item['runtimes']],key=lambda v:v.get('at',0),default={})
     if cached.get('status')=='ready' and now-cached.get('at',0)<300:
      proof=cached;code=0;fresh=True
     else:
      process=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
      try:process.communicate(timeout=100)
      except subprocess.TimeoutExpired:
       os.killpg(process.pid,signal.SIGTERM)
       try:process.communicate(timeout=5)
       except subprocess.TimeoutExpired:os.killpg(process.pid,signal.SIGKILL);process.communicate()
       raise
      proof=read(root/'verification_probe_latest.json');code=process.returncode;fresh=proof.get('at',0)>=now
     if fresh and code==0 and proof.get('status')=='ready' and clear_verified(item,proof):
      reserved.update(status='resumed',attempts=0,next_at=0)
     else:reserved.update(status='needs_attention' if reserved['attempts']>=LIMIT else 'cooling_down',last_status=proof.get('status') if fresh else 'probe_failed')
    except subprocess.TimeoutExpired:reserved.update(status='needs_attention' if reserved['attempts']>=LIMIT else 'cooling_down',last_status='probe_timeout')
    atomic_json(item['state'],reserved)
   if reserved['status']=='resumed' and item['service'] and not paused(item):
    subprocess.run(['systemctl','start',item['service']],check=True,timeout=20)
   results.append({'name':item['name'],**reserved})
  except RuntimeError as error:
   if 'Another collector uses' not in str(error):raise
   results.append({'name':item['name'],'status':'browser_busy','attempts':state.get('attempts',0)})
 atomic_json(GEO/'wenxin_retry_health.json',{'at':time.time(),'channels':results})
 print(json.dumps(results,ensure_ascii=False),flush=True)
if __name__=='__main__':
 with process_lock(GEO/'wenxin_retry.lock',blocking=False):run()

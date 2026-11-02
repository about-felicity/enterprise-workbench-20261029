import sys,json,time,hashlib,shutil
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.runtime import process_lock,atomic_json
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.api_worker import Worker
from geo_source_cards.pipeline_control import settings
root=runtime.job_root('creation-1793344766-1768de1c');base=Path('/opt/monitor/geo-content/maintenance/eye-http-recovery-20261030')
target=('2026-10-30','排行类',1)
class SingleArticleBudget(runtime.SharedBudget):
 def __init__(self,root):super().__init__(root);self.sent=0
 def reserve(self,payload,directory,meta,stage):
  assert stage=='writer' and tuple(meta.get(k) for k in ['date','category','number'])==target,'Outside authorized article'
  assert self.sent==0,'Only one paid request authorized'
  identity=super().reserve(payload,directory,meta,stage);self.sent+=1;return identity
with process_lock(root/'api/worker.lock',blocking=False):
 job=runtime.read(root/'job.json');assert job['budget_limits']=={'article_budget_cny':.35,'task_budget_cny':2.0}
 assert job['studio_plan_id']=='plan-7ec5b8a566c34569b4da63f14eed2741' and job['date']==target[0]
 original_settings=runtime.pipeline_control.settings
 shared_config=original_settings(runtime.SHARED);assert shared_config['article_budget_cny']==.35
 # Process-local approval; no shared configuration is changed.
 def approved_settings(path):
  config=original_settings(path)
  return {**config,'article_budget_cny':.4} if Path(path)==runtime.SHARED else config
 runtime.pipeline_control.settings=approved_settings
 oldpath=root/'queue/a70578f2ee060c94d08f7c36/ticket.json';old=runtime.read(oldpath)
 assert old['state']=='needs_attention' and old['error']=='API generation rejected: article_budget_exceeded'
 failedrun=root/'api/runs'/old['execution']['run_id'];assert not list(failedrun.rglob('api_state.json')) and not list(failedrun.rglob('response.json'))
 active=runtime.read(root/'api/active.json');assert active.get('state')=='SUBMITTED'
 assert runtime.read(root/'queue'/active['ticket']/'ticket.json')['state']=='accepted'
 files={}
 for p in (runtime.BASE/'runs').glob('*/job.json'):
  j=runtime.read(p)
  if j.get('studio_plan_id')==job['studio_plan_id'] and j.get('date')==job['date']:
   for f in (p.parent/'approved').rglob('*'):
    if f.is_file():files[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
 assert sum(x.endswith('/receipt.json') for x in files)==4
 audit=base/'budget-040-recovery.json';assert not audit.exists(),'Recovery already prepared; inspect before proceeding'
 atomic_json(audit,{'authorization':'REDACTED_CONFIGURE_LOCALLY','original_job':job,'old_ticket':old,'original_active':active,'preserved_files':files,'state':'prepared'})
 atomic_json(root/'job.json',{**job,'budget_limits':{**job['budget_limits'],'article_budget_cny':.4}})
 budget=None;client=None
 try:
  budget=SingleArticleBudget(root);client=CreationClient(runtime.KEY,budget=budget)
  assert client.balance()['is_available']
  meta={**old['meta'],'revision':old['meta'].get('revision',0)+1,'replaces':old['id'],'operator_budget_recovery':'eye-040-20261030'}
  replacement=publish_ticket(root,'writer',root/old['location'],list(old['inputs']),old['outputs'],meta)
  atomic_json(oldpath,{**old,'state':'revision_requested','replaced_by':replacement})
  worker=Worker(root,client,target_article=target);selected=worker.select(target[0]);assert selected['id']==replacement
  atomic_json(audit,{**runtime.read(audit),'state':'executing','replacement':replacement})
  print('EXECUTING',replacement,flush=True)
  result=worker.execute(selected,runtime.read(root/'api/active.json'))
  atomic_json(audit,{**runtime.read(audit),'state':'finished','result':result,'paid_requests':budget.sent})
  print('RESULT',json.dumps(result,ensure_ascii=False),'PAID_REQUESTS',budget.sent,flush=True)
 finally:
  current=runtime.read(root/'job.json');assert current['budget_limits']['article_budget_cny']==.4
  atomic_json(root/'job.json',{**current,'budget_limits':job['budget_limits']})
  if client is not None:client.close()
  if budget is not None:budget.db.close()
  atomic_json(audit,{**runtime.read(audit),'budget_restored':True,'finished_at':time.time()})
  assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in files.items())
  print('ORIGINAL_4_PRESERVED_AND_BUDGET_RESTORED',flush=True)

import sys,json,time,shutil
from pathlib import Path
from datetime import datetime
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,recovery
from geo_source_cards.runtime import atomic_json,process_lock
base=Path('/opt/monitor/geo-content/maintenance/recovery-20261027/budget-before');base.mkdir(exist_ok=True)
shutil.copy2(runtime.SHARED/'settings.json',base/'shared-settings.json')
runtime.pipeline_control.save_settings(runtime.SHARED,{'daily_budget_cny':30.0})
changed=[]
for root in (runtime.BASE/'runs').iterdir():
 j=runtime.read(root/'job.json');day=runtime.read(root/'days'/j.get('date','')/'day.json')
 if j.get('date','')<'2026-10-26' or runtime.read(root/'control.json').get('reason')=='plan_deleted' or day.get('status') in {'complete','complete_with_shortfall'}:continue
 if j.get('budget_limits'):
  shutil.copy2(root/'job.json',base/(root.name+'.json'));j['budget_limits']['task_budget_cny']=10.0;atomic_json(root/'job.json',j);changed.append(root.name)
 if runtime.read(root/'control.json').get('reason') in {'budget','budget_exceeded'}:
  if recovery.safe_original(root):
   runtime.resume(root,check_balance=False);recovery.succeeded(root)
now=datetime.now(studio.ZONE)
for path in (studio.ROOT/'days').glob('*/*.json'):
 t=runtime.read(path);p=t['plan'];day=t['date']
 if day<'2026-10-26' or day>now.date().isoformat() or day==now.date().isoformat() and p['capture_time']>now.strftime('%H:%M'):continue
 if p.get('deleted_at'):continue
 shutil.copy2(path,base/(t['daily_task_id']+'.json'))
 with process_lock(path.with_suffix('.lock'),blocking=True):
  t=runtime.read(path);t['plan']['task_budget_cny']=10.0;atomic_json(path,t)
print(json.dumps({'updated_unfinished_jobs':len(changed),'daily_budget':runtime.pipeline_control.settings(runtime.SHARED)['daily_budget_cny'],'article_budget':runtime.pipeline_control.settings(runtime.SHARED)['article_budget_cny']}))

import sys,json,time,hashlib,subprocess
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');lease=M/'budget-lease.json';settings=runtime.SHARED/'settings.json'
action=sys.argv[1]
with process_lock(runtime.SHARED/'control.lock',blocking=True):
 current=runtime.read(settings);state=runtime.read(lease)
 if action=='begin':
  if state.get('status')=='active':assert current['daily_budget_cny']==16;print('Existing budget lease active');raise SystemExit(0)
  assert current['daily_budget_cny']==10,'Unexpected shared budget; retain operator state'
  state={'status':'active','begin_epoch':time.time(),'expires_epoch':time.time()+4*3600,'original_cap':10,'temporary_cap':16,'plan_id':'plan-33e7bfca8bb6497da10b28f0444a693b','task_cap':5.25,'authorization':'User requested this 14-article test and replied 继续 after the explicit temporary-16 proposal; disclosed interpretation before execution','prior_settings':current,'control_sha256':hashlib.sha256((runtime.SHARED/'control.json').read_bytes()).hexdigest()}
  atomic_json(lease,state);atomic_json(settings,{**current,'daily_budget_cny':16})
 elif action=='restore':
  assert state.get('original_cap')==10
  if current['daily_budget_cny']==16:atomic_json(settings,{**current,'daily_budget_cny':10})
  elif current['daily_budget_cny']!=10:raise ValueError('Another operator changed the cap; not overwriting')
  state.update(status='restored',restored_epoch=time.time());atomic_json(lease,state)
 else:raise ValueError('Unknown action')
assert hashlib.sha256((runtime.SHARED/'control.json').read_bytes()).hexdigest()==state['control_sha256']
if action=='begin':
 subprocess.run(['systemd-run','--unit=geo-daohe-budget-restore-20261021','--on-active=4h','/home/user/geo-editorial/venv/bin/python','-B',str(M/'budget_lease.py'),'restore'],check=True)
print(json.dumps({'status':state['status'],'daily_cap':runtime.read(settings)['daily_budget_cny'],'task_cap':5.25,'original_control_unchanged':True},ensure_ascii=False))

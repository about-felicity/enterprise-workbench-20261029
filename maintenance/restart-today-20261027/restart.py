import sys,json,os,pwd,shutil,time
from pathlib import Path
from datetime import datetime
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime,materials
from geo_source_cards.runtime import atomic_json,process_lock
today=datetime.now(studio.ZONE).date().isoformat()
assert today=='2026-10-27'
base=Path('/opt/monitor/geo-content/maintenance/restart-today-20261027');base.mkdir(parents=True,exist_ok=True)
owner=pwd.getpwnam('user')
for pid in ['plan-53eaaebbc537459f81d55a3f8a43f969','plan-195abff2413a421dac589112f24c7596']:
 root=studio.capture_root(pid);p=studio.plan(pid);task=studio.ensure_day(p,today)
 assert p['enabled'] and p['capture_time']<=datetime.now(studio.ZONE).strftime('%H:%M')
 backup=base/pid;backup.mkdir(exist_ok=True)
 shutil.copy2(root/'settings.json',backup/'settings.json')
 dp=studio.day_path(pid,today);shutil.copy2(dp,backup/'day.json')
 with process_lock(dp.with_suffix('.lock'),blocking=True):
  task=runtime.read(dp);task['paused']=False;task['plan']['task_budget_cny']=10.0;atomic_json(dp,task)
 target=root/'days'/today;target.mkdir(exist_ok=True);os.chown(target,owner.pw_uid,owner.pw_gid);target.chmod(0o700)
 cfg=runtime.read(root/'settings.json')
 if not (target/'config.json').exists():
  atomic_json(target/'config.json',{**cfg,'questions':task['plan']['questions'],'rounds':task['plan'].get('rounds',1),'channels':task['plan']['channels'],'studio_plan':task['plan']})
  os.chown(target/'config.json',owner.pw_uid,owner.pw_gid);(target/'config.json').chmod(0o640)
 blocked=[]
 for model in task['plan']['channels']:
  for prior in materials.progress('2026-10-26',store_root=root):
   if prior['id']==model and studio.channel_verification_blocked(prior):
    bp=target/('blocked-'+model+'.json')
    if not bp.exists():atomic_json(bp,{'at':time.time(),'kind':'verification_required','inherited_from':'2026-10-26','reason':'Same persistent browser profile remains verification-blocked; restart only unblocked channels'})
    blocked.append(model)
 with process_lock(root/'settings.lock',blocking=True):
  cfg=runtime.read(root/'settings.json');cfg.update(requested_day=today,paused=False,paused_day='',restart_authorized_at=time.time());atomic_json(root/'settings.json',cfg)
 print(json.dumps({'plan':pid,'day':today,'resumed_channels':[m for m in p['channels'] if m not in blocked],'verification_preserved':blocked,'task_budget':10}))

import sys,json,time,hashlib,shutil
from pathlib import Path
from datetime import datetime,timedelta
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime
from geo_source_cards.runtime import atomic_json,process_lock
w=Path('/opt/monitor/maintenance/offpeak-schedule-20261102');w.mkdir(parents=True,exist_ok=True)
assert not (w/'applied.json').exists(),'Already applied; inspect rather than repeat'
plans=[p for p in studio.plans() if p.get('enabled') and p.get('frequency','daily')=='daily' and p.get('task_type','collect_write')=='collect_write']
plans.sort(key=lambda p:(-len(p['questions'])*p.get('rounds',1),-len(p['questions']),p['plan_id']))
assert len(plans)==14
rows=[];today=datetime.now(studio.ZONE).date().isoformat()
for i,p in enumerate(plans):
 minute=20+i*20;clock=f'{minute//60:02d}:{minute%60:02d}'
 root=studio.capture_root(p['plan_id']);planfile=studio.ROOT/'plans'/(p['plan_id']+'.json');settings=root/'settings.json'
 beforeplan=planfile.read_bytes();beforesettings=settings.read_bytes();cfg=runtime.read(settings)
 assert not p.get('legacy_capture')
 (w/(p['plan_id']+'-plan-before.json')).write_bytes(beforeplan);(w/(p['plan_id']+'-settings-before.json')).write_bytes(beforesettings)
 rows.append(dict(plan_id=p['plan_id'],name=p['name'],before=p['capture_time'],after=clock,plan_sha=hashlib.sha256(beforeplan).hexdigest(),settings_sha=hashlib.sha256(beforesettings).hexdigest(),questions=len(p['questions']),rounds=p.get('rounds',1)))
atomic_json(w/'proposal.json',{'rows':rows,'date':today})
for row,p in zip(rows,plans):
 root=studio.capture_root(p['plan_id']);planfile=studio.ROOT/'plans'/(p['plan_id']+'.json');settings=root/'settings.json'
 with process_lock(root/'settings.lock',blocking=True):
  assert hashlib.sha256(planfile.read_bytes()).hexdigest()==row['plan_sha']
  assert hashlib.sha256(settings.read_bytes()).hexdigest()==row['settings_sha']
  # Freeze today's already captured configuration before changing future times.
  captured=runtime.read(root/'days'/today/'config.json')
  if captured:studio.ensure_day(captured.get('studio_plan') or p,today)
  updated={**p,'capture_time':row['after'],'writing_time':row['after'],'revision':p.get('revision',0)+1,'updated_at':time.time()}
  cfg=runtime.read(settings)
  atomic_json(planfile,updated)
  atomic_json(settings,{**cfg,'time':row['after'],'studio_plan':updated})
  assert {k:v for k,v in updated.items() if k not in ['capture_time','writing_time','revision','updated_at']}=={k:v for k,v in p.items() if k not in ['capture_time','writing_time','revision','updated_at']}
  print(json.dumps(row,ensure_ascii=False),flush=True)
for row in rows:
 p=studio.plan(row['plan_id']);cfg=runtime.read(studio.capture_root(row['plan_id'])/'settings.json')
 assert p['capture_time']==p['writing_time']==cfg['time']==cfg['studio_plan']['capture_time']==row['after']
atomic_json(w/'applied.json',{'rows':rows,'at':datetime.now(studio.ZONE).isoformat(),'protected':['budgets','article_targets','questions','products','completed_today','geo_monitor_schedule']})
print('VERIFIED_14_PLANS_AND_CAPTURE_SETTINGS',flush=True)

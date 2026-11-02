import sys,json
from datetime import datetime
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime,materials
print('TIME',datetime.now(studio.ZONE).isoformat())
print('GEO_SCHEDULE',json.dumps({k:v for k,v in runtime.read(materials.GEO/'daily_plan.json').items() if k in ['time','enabled','timezone']},ensure_ascii=False))
for p in studio.plans():
 today=datetime.now(studio.ZONE).date().isoformat();r=studio.capture_root(p['plan_id']);cfg=runtime.read(r/'days'/today/'config.json');task=runtime.read(studio.day_path(p['plan_id'],today))
 print(json.dumps({k:p.get(k) for k in ['plan_id','name','enabled','frequency','task_type','capture_time','writing_time','start_date','legacy_capture','article_target','rounds','channels']}|{'questions':len(p.get('questions',[])),'today_capture_started':bool(cfg),'today_jobs':len(task.get('jobs',{})),'today_state':task.get('status')},ensure_ascii=False))

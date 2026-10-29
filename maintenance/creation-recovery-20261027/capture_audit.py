import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials
for p in studio.plans():
 root=studio.capture_root(p['plan_id'])
 for day in ['2026-10-26','2026-10-27']:
  if not (root/'days'/day/'config.json').exists():continue
  progress=materials.progress(day,store_root=root)
  if any(x.get('blocked') or x.get('recovery',{}).get('blocked') for x in progress):
   print(json.dumps({'name':p.get('name'),'date':day,'root':str(root),'settings':{k:v for k,v in runtime.read(root/'settings.json').items() if k in ['paused','paused_day','requested_day','time']},'progress':progress},ensure_ascii=False))

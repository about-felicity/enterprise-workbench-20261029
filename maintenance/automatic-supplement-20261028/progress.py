import sys,json,time,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials
pid='plan-0d57811d9b2543eab75d181badec6d9e';day='2026-10-26';t=runtime.read(studio.day_path(pid,day));s=runtime.read(studio.day_path(pid,day).with_suffix('.supplement-state'))
print('TASK',{k:t.get(k) for k in ['jobs','status','error','skipped_questions']});print('SUPPLEMENT',s)
if s.get('root'):
 root=Path(s['root']);print('HEALTH',runtime.read(root/'health.json'));print('PROGRESS',materials.progress(day,root))
for j in t.get('jobs',{}).values():
 root=runtime.job_root(j);print('JOB',j,runtime.read(root/'job.json').get('preparation'),runtime.read(root/'days'/day/'day.json'),runtime.read(root/'control.json'),len(runtime.articles(root)))
print('SCHEDULER',runtime.read(studio.ROOT/'health.json'))

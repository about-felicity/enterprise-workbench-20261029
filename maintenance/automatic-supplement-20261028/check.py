import sys,json,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
for name in ['materials.py','studio.py','search_capture.py','panel.html','supplement.py']:
 p=Path('/opt/monitor/geo-content/creation')/name
 print('HASH',name,hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None)
for p in (studio.ROOT/'capture').glob('*/health.json'):
 h=runtime.read(p)
 if h.get('active_channels'):print('ACTIVE',p.parent.name,h.get('active_channels'))
t=runtime.read(studio.day_path('plan-0d57811d9b2543eab75d181badec6d9e','2026-10-26'))
print('DYE', {k:t.get(k) for k in ['paused','status','jobs','skipped_questions']})
for p in (studio.ROOT/'days/2026-10-28').glob('*.json'):
 t=runtime.read(p)
 if t['plan'].get('name')=='科熙本防脱精华':print('FIRST',sum(len(runtime.articles(runtime.job_root(j))) for j in t['jobs'].values()),[runtime.read(runtime.job_root(j)/'days/2026-10-28/day.json').get('status') for j in t['jobs'].values()])

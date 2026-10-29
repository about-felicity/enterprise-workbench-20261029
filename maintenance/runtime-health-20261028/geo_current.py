import sqlite3,json,time
from pathlib import Path
p=Path('/opt/monitor/geo-capture/panel/control.sqlite')
with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 jobs=[dict(r) for r in db.execute('select j.* from jobs j join settings s on s.current_batch=j.batch')]
 print('JOBS',json.dumps(jobs,ensure_ascii=False))
for j in jobs:
 for key in ('root','runtime','runtime_root','path'):
  if j.get(key):print(key,j[key])
print('HEALTH')
for p in list(Path('/home/user/redroid-doubao/batches').glob('*20261028*/bridge_health.json'))+list(Path('/opt/monitor/geo-capture/panel/jobs').glob('*20261028*/*.json')):
 if 'health' in p.name or p.name=='job.json':
  try:print(str(p),p.read_text()[:6500])
  except Exception:pass

import json,sqlite3,datetime
from pathlib import Path
base=Path('/opt/monitor/geo-capture')
with sqlite3.connect((base/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 for row in db.execute("select * from jobs where batch like '%20261101%' or model like 'deepseek%' order by created desc limit 30"):
  r=dict(row);p=Path(r['health'])
  try:h=json.loads(p.read_text())
  except (OSError,ValueError):h={}
  print('JOB',json.dumps({'model':r['model'],'batch':r['batch'],'health_path':str(p),'created':r['created'],'health':h},ensure_ascii=False))
print('PLAN', (base/'daily_plan.json').read_text())

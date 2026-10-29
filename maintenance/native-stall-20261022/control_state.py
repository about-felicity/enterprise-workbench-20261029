import sqlite3,json
from pathlib import Path
path=Path('/opt/monitor/geo-capture/panel/control.sqlite')
with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 rows=[]
 for row in db.execute("select * from daily_tasks where day='2026-10-22' and model in ('doubao1','doubao2','yuanbao')"):
  r=dict(row);c=json.loads(r.pop('config'));r.update(questions=len(c['questions']),rounds=c['rounds'],interval=c['interval']);rows.append(r)
 print(json.dumps(rows,ensure_ascii=False))

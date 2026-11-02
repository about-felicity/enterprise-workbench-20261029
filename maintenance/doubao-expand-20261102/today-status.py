import sqlite3,json,subprocess
from pathlib import Path
b=Path('/opt/monitor/geo-capture')
with sqlite3.connect(b/'panel/control.sqlite') as db:
 for m in ('doubao3','doubao4'):
  row=db.execute("select status,error,batch from daily_tasks where model=? and day='2026-11-02'",(m,)).fetchone();print(m,row)
  if row and row[-1]:
   j=db.execute('select health,service from jobs where batch=?',(row[-1],)).fetchone()
   if j:
    h=json.loads(Path(j[0]).read_text());print(j[1],h.get('planned'),h.get('geo_processed'),h.get('status'),h.get('progress'),h.get('delivery_errors'))
print(Path('/proc/meminfo').read_text().splitlines()[2])

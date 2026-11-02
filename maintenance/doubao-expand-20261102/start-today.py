import sys,json,sqlite3
from pathlib import Path
b=Path('/opt/monitor/geo-capture');sys.path.insert(0,str(b))
from daily_tasks import DailyTasks,today
assert today()=='2026-11-02'
with sqlite3.connect(b/'panel/control.sqlite',timeout=20) as db:
 db.execute('begin immediate')
 for new,old in [('doubao3','doubao1'),('doubao4','doubao2')]:
  cfg=json.loads(db.execute('select config from daily_tasks where model=? and day=?',(old,today())).fetchone()[0])
  saved=json.loads(db.execute('select value from settings where model=?',(new,)).fetchone()[0])
  assert all(cfg[k]==saved[k] for k in ('questions','rounds','interval')) and len(cfg['questions'])==21 and cfg['rounds']==5
  DailyTasks.ensure_scheduled(None,db,new,today())
  print(new,db.execute('select desired,status,batch from daily_tasks where model=? and day=?',(new,today())).fetchone(),len(cfg['questions']),cfg['rounds'],cfg['interval'])

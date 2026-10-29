import sqlite3,json
from pathlib import Path
base=Path('/opt/monitor/asset-management');a=sqlite3.connect('file:'+str(base/'data/asset_management.db')+'?mode=ro',uri=True);a.row_factory=sqlite3.Row;b=sqlite3.connect('file:'+str(base/'initial-data/asset_management.db')+'?mode=ro',uri=True);b.row_factory=sqlite3.Row
for t in ['devices','assignments']:
 q='select * from '+t+' where '+('id' if t=='devices' else 'device_id')+' in (39,40)'
 print(t,'old',json.dumps([dict(r) for r in b.execute(q)],ensure_ascii=False),'now',json.dumps([dict(r) for r in a.execute(q)],ensure_ascii=False))
print('employee',json.dumps([dict(r) for r in a.execute('select id,name from employees where id=16')],ensure_ascii=False));print('user_exists',a.execute('select count(*) from users where id=16').fetchone()[0])

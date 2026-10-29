import sqlite3,json
from pathlib import Path
base=Path('/opt/monitor/asset-management')
a=sqlite3.connect('file:'+str(base/'data/asset_management.db')+'?mode=ro',uri=True);a.row_factory=sqlite3.Row
b=sqlite3.connect('file:'+str(base/'initial-data/asset_management.db')+'?mode=ro',uri=True);b.row_factory=sqlite3.Row
print('tables',a.execute("select name from sqlite_master where type='table'").fetchall())
cur={r['id']:dict(r) for r in a.execute('select * from devices')};old={r['id']:dict(r) for r in b.execute('select * from devices')}
print(json.dumps({'current_count':len(cur),'backup_count':len(old),'missing':[r for k,r in old.items() if k not in cur],'new_ids':[k for k in cur if k not in old]},ensure_ascii=False))
for k in old.keys()-cur.keys():
 print('related',json.dumps([dict(r) for r in b.execute('select a.*, e.name as employee_name from assignments a left join employees e on e.id=a.employee_id where device_id=?',(k,))],ensure_ascii=False))
print('current_tables_counts',[(t,a.execute('select count(*) from '+t).fetchone()[0]) for t in ['devices','assignments','employees','users']])

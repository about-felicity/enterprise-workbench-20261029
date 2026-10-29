import sqlite3,json
from pathlib import Path
base=Path('/opt/monitor/asset-management');dest=Path('/opt/monitor/maintenance/asset-device-recovery-20261026');dest.mkdir(exist_ok=True)
a=sqlite3.connect('file:'+str(base/'data/asset_management.db')+'?mode=ro',uri=True);a.row_factory=sqlite3.Row
backup=dest/'before-recovery.db'
if not backup.exists():
 with sqlite3.connect(backup) as out:a.backup(out)
 backup.chmod(0o600)
b=sqlite3.connect('file:'+str(base/'initial-data/asset_management.db')+'?mode=ro',uri=True);b.row_factory=sqlite3.Row
ids={r[0] for r in a.execute('select id from devices')};missing=[]
for r in b.execute('select id,device_code,device_type,brand,model from devices order by id'):
 if r['id'] in ids:continue
 d=dict(r);d['users']=[x[0] for x in b.execute('select e.name from assignments a join employees e on e.id=a.employee_id where a.device_id=?',(r['id'],))];missing.append(d)
(dest/'missing-candidates.json').write_text(json.dumps(missing,ensure_ascii=False,indent=2));print(json.dumps(missing,ensure_ascii=False))
print('Current database preserved; no business data modified.')

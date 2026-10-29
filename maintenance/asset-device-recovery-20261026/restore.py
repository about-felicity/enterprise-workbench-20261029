import sqlite3,json,datetime
from pathlib import Path
root=Path('/opt/monitor/asset-management');out=Path('/opt/monitor/maintenance/asset-device-recovery-20261026')
old=sqlite3.connect('file:'+str(root/'initial-data/asset_management.db')+'?mode=ro',uri=True);old.row_factory=sqlite3.Row
conn=sqlite3.connect(root/'data/asset_management.db',timeout=30);conn.row_factory=sqlite3.Row
with sqlite3.connect(out/'immediately-before-restore.db') as backup:conn.backup(backup)
(out/'immediately-before-restore.db').chmod(0o600)
def rows(table):return [dict(r) for r in conn.execute('select * from '+table+' order by id')]
conn.execute('pragma foreign_keys=ON');conn.execute('begin immediate')
try:
 before={t:rows(t) for t in ['devices','assignments','employees','users']}
 restored={}
 for table,col in [('devices','id'),('assignments','device_id')]:
  entries=[dict(r) for r in old.execute('select * from '+table+' where '+col+' in (39,40) order by id')];assert len(entries)==2
  assert not conn.execute('select 1 from '+table+' where '+col+' in (39,40)').fetchone()
  for row in entries:
   keys=list(row);conn.execute('insert into '+table+' ('+','.join(keys)+') values ('+','.join('?' for _ in keys)+')',[row[k] for k in keys])
  restored[table]=entries
 for table in before:
  after=rows(table);added={r['id'] for r in restored.get(table,[])}
  assert [r for r in after if r['id'] not in added]==before[table],table
 assert conn.execute('pragma integrity_check').fetchone()[0]=='ok'
 assert not conn.execute('pragma foreign_key_check').fetchall()
 conn.commit()
 result={'restored_device_ids':[39,40],'restored_assignment_ids':[37,38],'other_rows_unchanged':True,'device_count':len(rows('devices')),'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'evidence':'Latest successful DELETE requests: 2026-10-26 16:48:52 and 16:48:56 Asia/Shanghai'}
 (out/'recovery-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result))
 print(json.dumps([dict(r) for r in conn.execute('select d.id,d.device_code,d.status,e.name as current_user from devices d join assignments a on a.device_id=d.id join employees e on e.id=a.employee_id where d.id in (39,40) and a.returned_at is null')],ensure_ascii=False))
except Exception:
 conn.rollback();raise
finally:conn.close();old.close()

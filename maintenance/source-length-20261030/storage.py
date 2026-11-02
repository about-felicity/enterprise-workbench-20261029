import subprocess,json,sqlite3
from pathlib import Path
print('MONITOR_ROOT',[(p.name,p.is_dir()) for p in Path('/opt/monitor').iterdir()])
for p in Path('/opt/monitor').glob('*/doubao_source_content.db'):
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  print('CONTENT_DB',str(p),db.execute('select status,count(*) from source_content group by status').fetchall())
print('DATABASES',subprocess.check_output(['runuser','-u','postgres','--','psql','-At','-c',"select datname from pg_database where not datistemplate"]).decode())

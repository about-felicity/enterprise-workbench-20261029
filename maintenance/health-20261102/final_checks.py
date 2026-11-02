import json,sqlite3,subprocess,os
from pathlib import Path
base=Path('/opt/monitor')
for p in base.glob('*.db'):
 if 'doubao' not in p.name:continue
 with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
  tables=[r[0] for r in db.execute("select name from sqlite_master where type='table'")]
  print('DB',p.name,tables[:15])
  if 'responses' in tables:print('SCHEMA',list(db.execute('pragma table_info(responses)')))
work=base/'geo-content/maintenance/recovery-20261102/writer'
env=dict(os.environ,PYTHONPATH=str(base/'geo-content')+':'+str(base/'geo-content/engine'))
test=work/'test_response_format_recovery.py'
test.write_text(TEST)
r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B',str(test)],env=env,capture_output=True,text=True,timeout=60)
print('TESTS',r.stdout+r.stderr);assert r.returncode==0

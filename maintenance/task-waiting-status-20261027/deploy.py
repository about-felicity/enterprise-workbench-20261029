import json,hashlib,shutil,os,subprocess,py_compile
from pathlib import Path
base=Path('/opt/monitor/geo-content');rows=json.loads(Path('/tmp/task-waiting-status/manifest.json').read_text())
backup=base/'maintenance/task-waiting-status-20261027/before';backup.mkdir(parents=True,exist_ok=True)
for row in rows:
 p=base/'creation'/row['name'];candidate=Path('/tmp/task-waiting-status')/row['name']
 assert hashlib.sha256(candidate.read_bytes()).hexdigest()==row['new']
 if row['old'] is None:assert not p.exists()
 else:
  assert hashlib.sha256(p.read_bytes()).hexdigest()==row['old'],str(p)
  shutil.copy2(p,backup/p.name)
 if candidate.suffix=='.py':py_compile.compile(str(candidate),doraise=True)
for row in rows:
 p=base/'creation'/row['name'];candidate=Path('/tmp/task-waiting-status')/row['name'];tmp=p.with_suffix('.deploy-tmp')
 shutil.copyfile(candidate,tmp)
 if p.exists():os.chmod(tmp,p.stat().st_mode);os.chown(tmp,p.stat().st_uid,p.stat().st_gid)
 else:os.chmod(tmp,0o644)
 os.replace(tmp,p)
subprocess.run(['systemctl','restart','geo-content-api','geo-creation-studio'],check=True)
print(json.dumps({'deployed':[row['name'] for row in rows],'backup':str(backup)}))

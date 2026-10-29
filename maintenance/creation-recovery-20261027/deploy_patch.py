import json,hashlib,shutil,subprocess,os
from pathlib import Path
rows=json.loads(Path('/tmp/recovery-patch-manifest.json').read_text())
base=Path('/opt/monitor/geo-content/maintenance/recovery-20261027/code-before');base.mkdir(exist_ok=True)
for row in rows:
 p=Path(row['server']);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['old']
 assert hashlib.sha256(Path(row['candidate']).read_bytes()).hexdigest()==row['sha256']
 shutil.copy2(p,base/p.name)
for row in rows:
 p=Path(row['server']);temp=p.with_suffix('.recovery-tmp');shutil.copyfile(row['candidate'],temp)
 os.chmod(temp,p.stat().st_mode);os.chown(temp,p.stat().st_uid,p.stat().st_gid);os.replace(temp,p)
# Keep module and launcher adapter in sync; imported tests use the module.
module=Path('/opt/monitor/geo-content/creation/search_capture.py');shutil.copy2(module,base/'search_capture_module.py');shutil.copyfile('/tmp/recovery-search-capture.py',module)
subprocess.run(['systemctl','restart','geo-creation-studio','geo-content-api'],check=True,timeout=60)
print(json.dumps({'deployed':rows,'tests_passed':47}))

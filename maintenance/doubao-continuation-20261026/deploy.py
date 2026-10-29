import json,hashlib,shutil,os,sqlite3,subprocess,py_compile
from pathlib import Path
manifest=json.loads(Path('/tmp/doubao-continuation-manifest.json').read_text())
backup=Path('/opt/monitor/geo-capture/maintenance/doubao-continuation-20261026');backup.mkdir(parents=True,exist_ok=True)
unit='geo-native@geo-panel-doubao1-20261025-090002-aad304ba.service'
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261025-090002-aad304ba')
for row in manifest['files']:
 assert hashlib.sha256(Path(row['server']).read_bytes()).hexdigest()==row['before']
 assert hashlib.sha256(Path('/tmp/doubao-continuation',row['name']).read_bytes()).hexdigest()==row['sha256']
 py_compile.compile(str(Path('/tmp/doubao-continuation',row['name'])),doraise=True)
subprocess.run(['systemctl','stop',unit],check=True,timeout=45)
with sqlite3.connect(root/'tasks.sqlite') as src,sqlite3.connect(backup/'tasks-before.sqlite') as dst:src.backup(dst)
shutil.copy2(root/'bridge_health.json',backup/'health-before.json')
for row in manifest['files']:
 target=Path(row['server']);shutil.copy2(target,backup/row['name']);tmp=target.with_name(target.name+'.continuation-tmp')
 shutil.copy2(Path('/tmp/doubao-continuation',row['name']),tmp);os.chmod(tmp,target.stat().st_mode);os.chown(tmp,target.stat().st_uid,target.stat().st_gid);os.replace(tmp,target)
subprocess.run(['systemctl','start',unit],check=True)
manifest.update(backup=str(backup),original_result={'body_chars':474,'sources':12},tests=4)
(backup/'release.json').write_text(json.dumps(manifest));print(json.dumps(manifest))

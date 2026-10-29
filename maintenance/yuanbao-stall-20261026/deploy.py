import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261026-yuanbao-stall');R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261025-090004-5b28fa76');unit='geo-native@'+R.name+'.service'
manifest=json.loads(Path('/tmp/yuanbao26-manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (R/'maintenance_pause.json').exists(),'User pause must be preserved'
for row in manifest['files']:
 target=Path(row['server']);assert (sha(target) if target.exists() else None)==row['before'],row['server']
 assert sha(D/'stage'/row['source'])==row['sha256'],row['source']
B=D/'before-source';B.mkdir(exist_ok=False)
subprocess.run(['systemctl','mask','--runtime',unit],check=True)
subprocess.run(['systemctl','stop',unit],check=True,timeout=45)
try:
 with sqlite3.connect(R/'tasks.sqlite') as db:
  with sqlite3.connect(D/'before-tasks.sqlite') as out:db.backup(out)
 for row in manifest['files']:
  target=Path(row['server']);saved=B/row['source'];saved.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():shutil.copy2(target,saved)
  temp=target.with_name(target.name+'.repair26.tmp');shutil.copy2(D/'stage'/row['source'],temp);temp.chmod(0o644);os.replace(temp,target)
finally:
 subprocess.run(['systemctl','unmask','--runtime',unit],check=True)
 subprocess.run(['systemctl','daemon-reload'],check=True)
 subprocess.run(['systemctl','start',unit],check=True)
result={'at':time.time(),'files':manifest['files'],'queue_reset':False,'app_restarted':False,'only_reader_restarted':unit}
(D/'deployed.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

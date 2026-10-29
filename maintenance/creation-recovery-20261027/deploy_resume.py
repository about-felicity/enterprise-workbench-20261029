import sys,json,hashlib,shutil,os,subprocess
from pathlib import Path
root=Path('/opt/monitor/geo-content');p=root/'creation/runtime.py';new=Path('/tmp/recovery-runtime-resume.py')
manifest=json.loads(Path('/tmp/resume-manifest.json').read_text())
assert hashlib.sha256(p.read_bytes()).hexdigest()==manifest['old']
assert hashlib.sha256(new.read_bytes()).hexdigest()==manifest['new']
shutil.copy2(p,root/'maintenance/recovery-20261027/code-before/runtime.py')
temp=p.with_suffix('.tmp');shutil.copyfile(new,temp);os.chmod(temp,p.stat().st_mode);os.chown(temp,p.stat().st_uid,p.stat().st_gid);os.replace(temp,p)
sys.path[:0]=[str(root),str(root/'engine')]
from creation import runtime,recovery
from geo_source_cards.runtime import process_lock
resumed=[]
for folder in (runtime.BASE/'runs').iterdir():
 record=runtime.read(folder/'known_preflight_retry.json');control=runtime.read(folder/'control.json')
 job=runtime.read(folder/'job.json')
 if record.get('state')!='waiting' or control.get('paused') or not control.get('resumed_epoch') or job.get('date','')<'2026-10-26':continue
 if control.get('revision',0)<=record.get('control_revision',0):continue
 with process_lock(folder/'api/worker.lock',blocking=True):
  if recovery.safe_original(folder):recovery.succeeded(folder);resumed.append(folder.name)
subprocess.run(['systemctl','restart','geo-content-api','geo-creation-studio'],check=True)
print(json.dumps({'deployed':True,'cleared_obsolete_waits':resumed}))

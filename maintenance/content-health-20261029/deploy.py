import os,sys,json,time,hashlib,shutil,tarfile,subprocess
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/content-health-20261029');base.mkdir(parents=True,exist_ok=True)
creation=Path('/opt/monitor/geo-content/creation');stage=base/'stage';stage.mkdir(exist_ok=True)
shutil.copytree(creation,stage/'creation',dirs_exist_ok=True)
with tarfile.open('/tmp/content-health-20261029.tar.gz') as t:
 for n in ['supplement.py','test_rotation.py','test_original.py']:
  data=t.extractfile(n).read()
  if n=='test_original.py':data=data.replace(b'/tmp/supplement28-stage',str(stage).encode())
  (stage/('creation/supplement.py' if n=='supplement.py' else n)).write_bytes(data)
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-content/engine'}
for n in ['test_original.py','test_rotation.py']:
 r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B',str(stage/n)],env=env,capture_output=True,text=True,timeout=60)
 print(r.stdout+r.stderr,flush=True);assert r.returncode==0
p=creation/'supplement.py';assert hashlib.sha256(p.read_bytes()).hexdigest()=='b0027d889ee608b63e45c8ca0044c37f09f3aadd0fa333b788625d3b9736dc35'
# Only restart the scheduler between capture rounds, never a running writer.
active=[]
for h in Path('/opt/monitor/geo-content/studio/capture').glob('*/health.json'):
 if json.loads(h.read_text()).get('active_channels'):active.append(str(h))
assert not active,active
worker=subprocess.check_output(['systemctl','show','geo-content-worker','-p','MainPID']).decode()
backup=base/'supplement.before.py';assert not backup.exists();shutil.copy2(p,backup)
temp=p.with_suffix('.installing');shutil.copy2(stage/'creation/supplement.py',temp);temp.chmod(0o644);os.replace(temp,p)
try:
 subprocess.run(['systemctl','restart','geo-creation-studio'],check=True,timeout=30)
 for _ in range(20):
  health=json.loads(Path('/opt/monitor/geo-content/studio/health.json').read_text())
  if health.get('status')=='ready' and health.get('at',0)>time.time()-6:break
  time.sleep(1)
 else:raise RuntimeError('Scheduler health did not recover')
 assert worker==subprocess.check_output(['systemctl','show','geo-content-worker','-p','MainPID']).decode()
except Exception:
 shutil.copy2(backup,p);subprocess.run(['systemctl','restart','geo-creation-studio']);raise
release={'files':[{'source':'geo-monitor-deploy/creation/supplement.py','server':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}],'tests':8,'writer_unchanged':True,'at':time.time()}
(base/'release.json').write_text(json.dumps(release,indent=2));print(json.dumps(release),flush=True)

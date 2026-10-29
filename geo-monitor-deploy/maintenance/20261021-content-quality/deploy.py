"""Apply source changes only at a paid-request-safe boundary; no task resume."""
import json,shutil,subprocess,sys,time,zipfile
from pathlib import Path
B=Path('/opt/monitor/geo-content');R=Path('/opt/monitor/geo-capture/maintenance/20261021-content-quality');S=R/'stage'
R.mkdir(exist_ok=True)
if not S.exists():
 S.mkdir();shutil.copytree(B/'engine',S/'engine');shutil.copytree(B/'creation',S/'creation')
with zipfile.ZipFile('/tmp/creation-quality-patch.zip') as z:
 for n in z.namelist():
  p=S/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n))
env=dict(__import__('os').environ,PYTHONPATH=str(S)+':'+str(S/'engine'))
py='/home/user/geo-editorial/venv/bin/python'
subprocess.run([py,'-B','-m','unittest','discover','-s',str(S/'tests'),'-p','test_consumer_voice.py'],env=env,check=True)
subprocess.run([py,'-B','-m','unittest','creation.test_download_service','creation.test_materials','creation.test_studio','creation.test_workflow','creation.test_client_projection'],env=env,check=True)
if '--apply' not in sys.argv:sys.exit(0)
def read(p):return json.loads(p.read_text()) if p.exists() else {}
controls={}
for p in (B/'runtime/runs').glob('*/job.json'):
 controls[p.parent.name]=read(p.parent/'control.json')
 assert read(p.parent/'api/active.json').get('state') in (None,'SUBMITTED'),str(p)
 assert not any(read(t).get('state')=='claimed' for t in (p.parent/'queue').glob('*/ticket.json')),str(p)
version=next((s.split('=',1)[1] for s in sys.argv if s.startswith('--version=')), 'v2' if '--v2' in sys.argv else 'v1')
backup=R/('backup' if version=='v1' else 'backup-'+version);assert not backup.exists(),'Already deployed'
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 backup.mkdir()
 with zipfile.ZipFile('/tmp/creation-quality-patch.zip') as z:
  for n in z.namelist():
   if n.startswith('tests/'):continue
   target=B/n;old=backup/n;old.parent.mkdir(parents=True,exist_ok=True)
   if target.exists():shutil.copy2(target,old)
   target.write_bytes(z.read(n))
 for job,control in controls.items():assert read(B/'runtime/runs'/job/'control.json')==control
 (R/'deployment.json').write_text(json.dumps({'at':time.time(),'task_controls_unchanged':True,'paid_requests_replayed':0,'main_geo_untouched':True},indent=2))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print('Applied; controls unchanged')

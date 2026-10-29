import json,os,shutil,subprocess,sys,time,zipfile
from pathlib import Path
B=Path('/opt/monitor/geo-content');R=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');R.mkdir(exist_ok=True)
S=R/'stage'
if not S.exists():
 S.mkdir();shutil.copytree(B/'engine',S/'engine');shutil.copytree(B/'creation',S/'creation')
 shutil.copytree(Path('/opt/monitor/geo-capture/maintenance/20261021-content-quality/stage/tests'),S/'tests')
with zipfile.ZipFile('/tmp/product-richness21.zip') as z:z.extractall(S)
env={**os.environ,'PYTHONPATH':str(S)+':'+str(S/'engine')};py='/home/user/geo-editorial/venv/bin/python'
subprocess.run([py,'-B','-m','unittest','discover','-s',str(S/'tests')],env=env,check=True)
subprocess.run([py,'-B','-m','unittest','creation.test_materials','creation.test_studio','creation.test_workflow','creation.test_client_projection','creation.test_download_service'],env=env,check=True)
if '--apply' not in sys.argv:raise SystemExit(0)
engine_only='--engine-only' in sys.argv
marker=R/('deployed-v2.json' if engine_only else 'deployed.json')
assert not marker.exists(),'Deployment already applied'
def read(p):return json.loads(p.read_text()) if p.exists() else {}
controls={p.parent.name:read(p.parent/'control.json') for p in (B/'runtime/runs').glob('*/job.json')}
for name in controls:
 root=B/'runtime/runs'/name
 assert read(root/'api/active.json').get('state') in (None,'SUBMITTED'),'Paid request is active'
 assert not any(read(p).get('state')=='claimed' for p in (root/'queue').glob('*/ticket.json'))
pid=int(subprocess.check_output(['systemctl','show','geo-creation-studio','--property=MainPID','--value']))
rows=[tuple(map(int,line.split())) for line in subprocess.check_output(['ps','-eo','pid=,ppid='],text=True).splitlines()]
children={a for a,b in rows if b==pid}
assert engine_only or not any(b in children for a,b in rows),'A creation capture is in flight; wait for its safe boundary'
backup=R/('backup-v2' if engine_only else 'backup');backup.mkdir()
services=['geo-content-worker'] if engine_only else ['geo-creation-studio','geo-content-worker']
subprocess.run(['systemctl','stop',*services],check=True)
try:
 with zipfile.ZipFile('/tmp/product-richness21.zip') as z:
  for name in z.namelist():
   if name.startswith('tests/') or (engine_only and not (name.startswith('engine/') or name=='creation/article_export.py')):continue
   target=B/name;old=backup/name;old.parent.mkdir(parents=True,exist_ok=True)
   if target.exists():shutil.copy2(target,old)
   temp=target.with_suffix(target.suffix+'.new');temp.write_bytes(z.read(name));temp.chmod(0o644);temp.replace(target)
 for name,c in controls.items():assert read(B/'runtime/runs'/name/'control.json')==c
 marker.write_text(json.dumps({'at':time.time(),'task_controls_unchanged':True,'studio_restarted':not engine_only,'main_geo_collectors_untouched':True}))
finally:subprocess.run(['systemctl','start',*services],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print('Product detail contracts and genre quotas applied')

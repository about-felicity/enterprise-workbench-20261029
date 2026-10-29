import json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
R=Path('/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall');B=Path('/home/user/redroid-yuanbao');S=R/'stage'
assert not (R/'deployed.json').exists(),'One-off deployment already applied'
S.mkdir(exist_ok=True)
for p in B.iterdir():
 if p.is_file() and p.suffix in ('.py','.js'):shutil.copy2(p,S/p.name)
shutil.copytree(B/'tests',S/'tests',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(B/'tools',S/'tools',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
for source,target in [('/tmp/yuanbao-binding-recovery21.py','binding_recovery.py'),('/tmp/yuanbao-native-client21.py','native_client.py'),('/tmp/yuanbao-exact-probe.js','native_models.js'),('/tmp/test-yuanbao-binding-recovery21.py','tests/test_binding_recovery.py')]:shutil.copy2(source,S/target)
env={**os.environ,'PYTHONPATH':str(S)+':/home/user/redroid-doubao/geo-batch-code:/home/user/redroid-doubao'}
py='/home/user/redroid-doubao/worker-venv/bin/python'
subprocess.run([py,'-B','-m','unittest','discover','-s',str(S/'tests')],env=env,check=True)
batch='geo-panel-yuanbao-20261021-090004-d6fb7a84';root=B/'batches'/batch;unit='geo-native@'+batch
backup=R/'backup';assert not backup.exists();backup.mkdir()
with sqlite3.connect('file:'+str(root/'tasks.sqlite')+'?mode=ro',uri=True) as db,sqlite3.connect(backup/'tasks.sqlite') as out:db.backup(out)
for name in ('native_client.py','native_models.js'):
 shutil.copy2(B/name,backup/name)
for p in root.glob('1267aeb4-acc9-5ee7-b8d8-2439199ba4e8*.json'):shutil.copy2(p,backup/p.name)
subprocess.run(['systemctl','stop',unit],check=True,timeout=50)
try:
 for name in ('native_client.py','native_models.js','binding_recovery.py'):
  temp=B/(name+'.quality-new');shutil.copy2(S/name,temp);temp.chmod(0o644);temp.replace(B/name)
 shutil.copy2(S/'tests/test_binding_recovery.py',B/'tests/test_binding_recovery.py')
 (R/'deployed.json').write_text(json.dumps({'at':time.time(),'batch':batch,'app_restarted':False,'questions_resent':0,'other_workers_restarted':False}))
finally:subprocess.run(['systemctl','start',unit],check=True)
print('Applied only Yuanbao reader; original task and App preserved')

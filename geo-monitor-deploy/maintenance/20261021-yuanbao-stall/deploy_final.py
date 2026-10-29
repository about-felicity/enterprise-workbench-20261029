import json,os,shutil,subprocess,time
from pathlib import Path
R=Path('/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall');B=Path('/home/user/redroid-yuanbao');S=R/'stage'
assert (R/'deployed-v2.json').exists() and not (R/'deployed-v3.json').exists()
for source,name in [('/tmp/yuanbao-native-client-v3.py','native_client.py'),('/tmp/yuanbao-native-models-v3.js','native_models.js'),('/tmp/test-yuanbao-client21.py','tests/test_native_client_recovery.py'),('/tmp/test-yuanbao-history21.py','tests/test_history_refresh.py')]:shutil.copy2(source,S/name)
env={**os.environ,'PYTHONPATH':str(S)+':/home/user/redroid-doubao/geo-batch-code:/home/user/redroid-doubao'}
subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-B','-m','unittest','discover','-s',str(S/'tests')],env=env,check=True)
backup=R/'backup-v3';backup.mkdir()
for name in ('native_client.py','native_models.js'):shutil.copy2(B/name,backup/name)
unit='geo-native@geo-panel-yuanbao-20261021-090004-d6fb7a84'
subprocess.run(['systemctl','stop',unit],check=True,timeout=50)
try:
 for name in ('native_client.py','native_models.js'):
  temp=B/(name+'.new');shutil.copy2(S/name,temp);temp.chmod(0o644);temp.replace(B/name)
 for name in ('test_native_client_recovery.py','test_history_refresh.py'):shutil.copy2(S/'tests'/name,B/'tests'/name)
 (R/'deployed-v3.json').write_text(json.dumps({'at':time.time(),'render_only_candidate_is_pending_not_transport_failure':True,'unknown_resends':0}))
finally:subprocess.run(['systemctl','start',unit],check=True)
print('Final native recovery deployed')

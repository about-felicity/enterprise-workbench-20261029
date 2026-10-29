import ast,json,os,shutil,subprocess,time
from pathlib import Path
R=Path('/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall');B=Path('/home/user/redroid-yuanbao');S=R/'stage'
assert (R/'deployed.json').exists() and not (R/'deployed-v2.json').exists()
files=[('/tmp/yuanbao-history-refresh21.py',B/'history_refresh.py'),('/tmp/yuanbao-native-core21.py',B/'native_core.py'),('/tmp/question-only-worker-yuanbao21.py',Path('/home/user/redroid-doubao/geo-batch-code/question_only_worker.py'))]
for source,destination in files:
 ast.parse(Path(source).read_text());shutil.copy2(source,S/destination.name)
for source,name in [('/tmp/test-yuanbao-history21.py','test_history_refresh.py'),('/tmp/test-yuanbao-native-core21.py','test_native_core.py')]:shutil.copy2(source,S/'tests'/name)
env={**os.environ,'PYTHONPATH':str(S)+':/home/user/redroid-doubao/geo-batch-code:/home/user/redroid-doubao'}
py='/home/user/redroid-doubao/worker-venv/bin/python'
subprocess.run([py,'-B','-m','unittest','discover','-s',str(S/'tests')],env=env,check=True)
# Actual historical request store must satisfy the same pure identity gate.
code='from history_refresh import stored_history;import json;from pathlib import Path;r=Path("/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall");d=json.loads((r/"inspect.json").read_text());p=stored_history(d["binding"],d["task"],json.loads((r/"original-native.json").read_text()));assert p and p["conversation_id"]=="0RPgFhBs0yO";print("Original store proof passed; no navigation or send")'
subprocess.run([py,'-B','-c',code],env=env,check=True)
backup=R/'backup-v2';backup.mkdir()
for source,destination in files:
 if destination.exists():shutil.copy2(destination,backup/destination.name)
unit='geo-native@geo-panel-yuanbao-20261021-090004-d6fb7a84'
subprocess.run(['systemctl','stop',unit],check=True,timeout=50)
try:
 for source,destination in files:
  temp=destination.with_suffix(destination.suffix+'.new');shutil.copy2(source,temp);temp.chmod(0o644);temp.replace(destination)
 for name in ('test_history_refresh.py','test_native_core.py'):shutil.copy2(S/'tests'/name,B/'tests'/name)
 (R/'deployed-v2.json').write_text(json.dumps({'at':time.time(),'original_task_retained':True,'other_collectors_restarted':False,'history_refresh_max_attempts_per_task':2,'minimum_backoff_seconds':600,'original_questions_resent':0}))
finally:subprocess.run(['systemctl','start',unit],check=True)
print('Bounded original-request readback recovery deployed')

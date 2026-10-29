import ast,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
R=Path('/opt/monitor/geo-capture/maintenance/20261021-doubao-stall');B=Path('/home/user/redroid-doubao/geo-batch-code');S=R/'stage';S.mkdir(exist_ok=True)
assert not (R/'deployed.json').exists(),'Already applied; do not replay one-off deployment'
for p in B.glob('*.py'):shutil.copy2(p,S/p.name)
(S/'tests').mkdir(exist_ok=True)
for source,name in [('/tmp/doubao-tips-core21.py','question_only_core.py'),('/tmp/doubao-tips-worker21.py','question_only_worker.py'),('/tmp/test-doubao-tips21.py','tests/test_question_only.py'),('/tmp/test-doubao-zero-tips21.py','tests/test_native_zero_sources.py')]:
 ast.parse(Path(source).read_text());shutil.copy2(source,S/name)
env={**os.environ,'PYTHONPATH':str(S)+':/home/user/redroid-doubao:/home/user/redroid-yuanbao'};py='/home/user/redroid-doubao/worker-venv/bin/python'
subprocess.run([py,'-B','-m','unittest','discover','-s',str(S/'tests')],env=env,check=True)
code='from question_only_core import lookup_bound;import json;from pathlib import Path;d=json.loads(Path("/opt/monitor/geo-capture/maintenance/20261021-doubao-stall/inspect.json").read_text());r=lookup_bound(d["task"],d["binding"]);assert r["status"]=="complete" and len(r["sources"])==11 and len(r["native_tips"])==1;Path("/opt/monitor/geo-capture/maintenance/20261021-doubao-stall/staged-result.json").write_text(json.dumps(r,ensure_ascii=False));print("Real original answer passed staged parsing")'
subprocess.run([py,'-B','-c',code],env=env,check=True)
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261021-090003-e1d20b1d');backup=R/'backup';backup.mkdir()
with sqlite3.connect('file:'+str(root/'tasks.sqlite')+'?mode=ro',uri=True) as db,sqlite3.connect(backup/'tasks.sqlite') as out:db.backup(out)
for name in ('question_only_core.py','question_only_worker.py'):shutil.copy2(B/name,backup/name)
unit='geo-native@'+root.name;subprocess.run(['systemctl','stop',unit],check=True,timeout=50)
try:
 for name in ('question_only_core.py','question_only_worker.py'):
  temp=B/(name+'.new');shutil.copy2(S/name,temp);temp.chmod(0o644);temp.replace(B/name)
 (R/'deployed.json').write_text(json.dumps({'at':time.time(),'original_batch':root.name,'questions_resent':0,'other_workers_restarted':False,'app_restarted':False}))
finally:subprocess.run(['systemctl','start',unit],check=True)
print('Original Doubao1 batch resumed; tips retained, no resend')

import json,hashlib,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];M=Path(__file__).parent;files={};targets={}
for group,base in [('doubao',W/'source-snapshot/server/home/user/redroid-doubao/geo-batch-code'),('yuanbao',W/'source-snapshot/server/home/user/redroid-yuanbao')]:
 for p in base.rglob('*'):
  if p.is_file():files[group+'/'+p.relative_to(base).as_posix()]=p
files['shared/runtime_reliability.py']=W/'geo-monitor-deploy/runtime_reliability.py'
targets['shared/runtime_reliability.py']='/opt/monitor/geo-capture/runtime_reliability.py'
files['shared/native_memory_policy.json']=W/'geo-monitor-deploy/config/native_memory_policy.json';targets['shared/native_memory_policy.json']='/opt/monitor/geo-capture/native_memory_policy.json'
for group,target in [('doubao','/home/user/redroid-doubao/geo-batch-code'),('yuanbao','/home/user/redroid-yuanbao')]:
 files[group+'/runtime_reliability.py']=W/'geo-monitor-deploy/runtime_reliability.py';targets[group+'/runtime_reliability.py']=target+'/runtime_reliability.py'
for name in ('question_only_worker.py','question_only_adapters.py','question_only_core.py','draft_submission_recovery.py','native_readback_guard.py','native_memory_guard.py'):
 files['doubao/'+name]=W/'redroid-deploy'/name;targets['doubao/'+name]='/home/user/redroid-doubao/geo-batch-code/'+name
for p in (W/'redroid-deploy/tests').glob('test_*.py'):files['doubao/tests/'+p.name]=p
for name in ('native_core.py','native_client.py','native_storage.py','history_refresh.py'):
 files['yuanbao/'+name]=W/'yuanbao-deploy'/name;targets['yuanbao/'+name]='/home/user/redroid-yuanbao/'+name
for p in (W/'yuanbao-deploy/tests').glob('test_*.py'):files['yuanbao/tests/'+p.name]=p
for name in ('test_native_core.py','test_native_client_recovery.py','test_history_refresh.py'):targets['yuanbao/tests/'+name]='/home/user/redroid-yuanbao/tests/'+name
targets['doubao/tests/test_draft_submission_recovery.py']='/home/user/redroid-doubao/geo-batch-code/tests/test_draft_submission_recovery.py'
targets['doubao/tests/test_native_readback_guard.py']='/home/user/redroid-doubao/geo-batch-code/tests/test_native_readback_guard.py'
targets['doubao/tests/test_native_memory_guard.py']='/home/user/redroid-doubao/geo-batch-code/tests/test_native_memory_guard.py'
targets['doubao/tests/test_native_zero_sources.py']='/home/user/redroid-doubao/geo-batch-code/tests/test_native_zero_sources.py'
mapping={}
deployed=json.loads((M/'deployed-source.json').read_text())['files'] if (M/'deployed-source.json').exists() else {}
for name,target in targets.items():
 old=W/'source-snapshot/server'/target.lstrip('/')
 if name=='shared/native_memory_policy.json':old=W/'source-snapshot/local/geo-monitor-deploy/config/native_memory_policy.json'
 mapping[name]={'target':target,'sha256':hashlib.sha256(files[name].read_bytes()).hexdigest(),'before':deployed.get(target,hashlib.sha256(old.read_bytes()).hexdigest() if old.is_file() else None)}
output=W/'geo-monitor-deploy/maintenance/native-stall22.zip'
with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
 for name,p in files.items():z.writestr(name,p.read_bytes())
 z.writestr('manifest.json',json.dumps(mapping))
(M/'deployment-manifest.json').write_text(json.dumps(mapping,indent=2));print(json.dumps({'files':len(files),'targets':len(targets)}))

import ast
import json
from pathlib import Path
import shutil
import sys
import time
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,operation,lane,atomic,read
base=Path('/opt/monitor/geo-capture');root=base/'maintenance/20261015-unified/native-lease-upgrade';root.mkdir(mode=0o700,exist_ok=True)
api=API();models=['doubao1','doubao2','yuanbao']
initial=root/'before.json'
if not initial.exists():atomic(initial,{m:lane(api.panel(),m)['current'] for m in models})
before=read(initial)
for model in models:
    assert lane(api.panel(),model)['current']['batch']==before[model]['batch']
    operation(root,api,model+'-pause-for-lease',model,'pause',{})
print(json.dumps({'phase':'draining_original_native_jobs'}),flush=True)
until=time.time()+300
while True:
    currents={m:lane(api.panel(),m)['current'] for m in models}
    if all(c['service_state'] not in {'active','activating','deactivating'} for c in currents.values()):break
    if time.time()>until:raise RuntimeError('Did not drain; no forced restart or unknown reset')
    time.sleep(3)
assert all(c['batch']==before[m]['batch'] and not c['needs_review'] and c['captured']==c['processed'] for m,c in currents.items())
source=Path('/tmp/question_only_worker.lease.py');ast.parse(source.read_text())
target=Path('/home/user/redroid-doubao/geo-batch-code/question_only_worker.py')
if not (root/'question_only_worker.before.py').exists():shutil.copy2(target,root/'question_only_worker.before.py')
shutil.copyfile(source,target)
for model in models:
    operation(root,api,model+'-resume-same-job',model,'resume',{})
atomic(root/'report.json',{'at':time.time(),'same_batches':{m:c['batch'] for m,c in currents.items()},'drained_counts':{m:c['processed'] for m,c in currents.items()},'heartbeat_lease_seconds':150,'reason':'Bounded 75s ready plus 30s send must not use 45s lease','unknown_resends':0})
print(json.dumps({'phase':'resumed_same_native_jobs','lease_seconds':150}),flush=True)

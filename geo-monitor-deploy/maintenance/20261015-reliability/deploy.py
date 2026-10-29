"""One recoverable release, draining existing jobs; never creates model tasks."""
import ast,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,operation,atomic,read,lane

base=Path('/opt/monitor/geo-capture');stage=Path('/tmp/geo-reliability-stage')
root=base/'maintenance/20261015-reliability';root.mkdir(mode=0o700,exist_ok=True)
api=API();pointer=read(base/'soak12h_current.json');manifest=read(Path(pointer['root'])/'manifest.json')
models=list(manifest['jobs']);before_path=root/'before.json'
if not before_path.exists():
    panel=api.panel();before={m:lane(panel,m)['current'] for m in models}
    assert all(c['batch']==manifest['jobs'][m]['batch'] and not c['needs_review'] for m,c in before.items())
    atomic(before_path,before)
before=read(before_path)
if (root/'deployed.json').exists():print(json.dumps({'already_deployed':True}));raise SystemExit(0)
atomic(root/'maintenance.json',{'at':time.time(),'reason':'User-authorized reliability upgrade; original queues drained without resend','old_capture_test':pointer['test_id']})
for model in models:
    assert lane(api.panel(),model)['current']['batch']==before[model]['batch']
    operation(root,api,model+'-drain',model,'pause',{})
print(json.dumps({'phase':'draining_six_existing_jobs'}),flush=True)
until=time.time()+1200
while True:
    currents={m:lane(api.panel(),m)['current'] for m in models}
    if all(c['service_state'] not in {'active','activating','reloading','deactivating'} for c in currents.values()):break
    if time.time()>until:raise RuntimeError('Drain timeout; no forced termination or unknown reset')
    time.sleep(3)
assert all(c['batch']==before[m]['batch'] and not c['needs_review'] and c['captured']==c['processed'] for m,c in currents.items())
atomic(root/'drained.json',{'at':time.time(),'models':currents})
files=read(stage/'manifest.json')['files'];backup=root/'backup'
for entry in files:
    source=stage/entry['stage'];data=source.read_bytes()
    assert hashlib.sha256(data).hexdigest()==entry['sha256']
    if source.suffix=='.py':ast.parse(data.decode('utf-8-sig'))
    for name in entry['targets']:
        target=Path(name);saved=backup/name.lstrip('/')
        if target.exists() and not saved.exists():saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
        shutil.copyfile(source,target)
        if not os.access(target,os.R_OK):os.chmod(target,0o644)
subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
api=API()
for attempt in range(20):
    try:api.panel();break
    except Exception:
        if attempt==19:raise
        time.sleep(1)
operation(root,api,'deepseek-login-check','deepseek','login',{})
until=time.time()+150
while lane(api.panel(),'deepseek')['login_status']['status']=='checking' and time.time()<until:time.sleep(3)
assert lane(api.panel(),'deepseek')['login_status']['status']=='ready','DS login check failed; no forced resume'
for model in models:
    assert lane(api.panel(),model)['current']['batch']==before[model]['batch']
    operation(root,api,model+'-resume-original',model,'resume',{})
result={'at':time.time(),'same_batches':{m:c['batch'] for m,c in currents.items()},
        'drained_counts':{m:c['processed'] for m,c in currents.items()},'files':files,
        'unknown_resends':0,'new_batches':0,'core_or_android_restarts':0}
atomic(root/'deployed.json',result)
print(json.dumps({'phase':'deployed_resumed_same_six_jobs','drained_counts':result['drained_counts']}),flush=True)

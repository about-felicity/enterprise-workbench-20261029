from datetime import datetime,timezone
import ast,hashlib,json,math,shutil,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,atomic,lane,read
base=Path('/opt/monitor/geo-capture');pointer=base/'soak12h_current.json';old=read(pointer)
if old['test_id'].startswith('question-only-soak12h-reliability-'):
    print(json.dumps(old));raise SystemExit(0)
assert old['test_id']=='question-only-soak12h-fencefix-1792063163'
release=read(base/'maintenance/20261015-reliability/deployed.json')
oldroot=Path(old['root']);manifest=read(oldroot/'manifest.json');status=read(oldroot/'status.json')
api=API();panel=api.panel()
for model,job in manifest['jobs'].items():
    value=lane(panel,model)['current']
    assert value['batch']==job['batch'] and value['service_state'] in {'active','activating'} and not value['needs_review'],value
subprocess.run(['systemctl','disable','--now',old['service'],old['deadline_timer']],check=True)
status.update(status='interrupted',interrupted_at=time.time(),reason='User-authorized reliability upgrade: six original jobs drained and resumed; no forced kill, no new batch, no unknown resend. This interrupted version window is not a 12h pass.')
atomic(oldroot/'interrupted_report.json',status);atomic(oldroot/'status.json',status)
target=base/'all_channel_soak.py';source=Path('/tmp/all_channel_soak.reliability.py');ast.parse(source.read_text())
shutil.copy2(target,base/'maintenance/20261015-reliability/all_channel_soak.before.py');shutil.copyfile(source,target)
start=time.time();test_id='question-only-soak12h-reliability-'+str(int(start));root=base/'soak'/test_id;root.mkdir(mode=0o700)
manifest.update(test_id=test_id,started_at=start,deadline=start+43200,supersedes=old['test_id'],
    window_baseline={m:lane(panel,m)['current'] for m in manifest['jobs']},
    reliability_release={'deployed_at':release['at'],'evidence':'maintenance/20261015-reliability/deployed.json'},
    scope=manifest['scope']+' Reliability v2: finite native hydration/read retries, EOF double-read fence, durable same-RID delivery backoff, browser backpressure and cooperative pre-send drain. Same tasks and questions; cumulative vs window deltas/carry-in reported separately.')
for value in manifest['window_baseline'].values():value['verified_unique_receipts']=value['unique_processed']
manifest['docker_before']=subprocess.check_output(['docker','inspect',*manifest['containers'],'--format','{{.Name}} {{.State.StartedAt}}'],text=True).strip()
atomic(root/'manifest.json',manifest)
oldunit=old['service'].removesuffix('.service');unit='geo-'+test_id
when=datetime.fromtimestamp(math.ceil(manifest['deadline']),timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
for suffix in ['.service','-deadline.service','-deadline.timer']:
    text=(Path('/etc/systemd/system')/(oldunit+suffix)).read_text().replace(str(oldroot),str(root)).replace(oldunit,unit)
    if suffix.endswith('.timer'):text='\n'.join('OnCalendar='+when if line.startswith('OnCalendar=') else line for line in text.splitlines())+'\n'
    (Path('/etc/systemd/system')/(unit+suffix)).write_text(text)
value={**{k:manifest[k] for k in ('test_id','started_at','deadline','duration_seconds')},'root':str(root),'service':unit+'.service','deadline_timer':unit+'-deadline.timer'}
atomic(pointer,value);subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now',unit+'.service',unit+'-deadline.timer'],check=True)
export=Path('/tmp/geo-reliability-pointer.json');export.write_text(json.dumps(value));export.chmod(0o644)
print(json.dumps(value))

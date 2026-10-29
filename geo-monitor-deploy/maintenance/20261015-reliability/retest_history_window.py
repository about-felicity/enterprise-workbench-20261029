"""Start a fresh recorder window over the same six jobs after an evidenced fix."""
from datetime import datetime,timezone
import json,math,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,atomic,lane,read
base=Path('/opt/monitor/geo-capture');pointer=base/'soak12h_current.json';old=read(pointer)
if old['test_id'].startswith('question-only-soak12h-rowidfix-'):
    print(json.dumps(old));raise SystemExit(0)
assert old['test_id']=='question-only-soak12h-videofix-1792066775'
fix=read(base/'maintenance/20261015-reliability/doubao-history-row-fix/deployed.json')
oldroot=Path(old['root']);manifest=read(oldroot/'manifest.json');status=read(oldroot/'status.json')
api=API();panel=api.panel()
for model,job in manifest['jobs'].items():
    value=lane(panel,model)['current']
    assert value['batch']==job['batch'] and value['service_state'] in {'active','activating'} and not value['needs_review']
assert lane(panel,'doubao1')['current']['processed']>=188
subprocess.run(['systemctl','disable','--now',old['service'],old['deadline_timer']],check=True)
status.update(status='interrupted',interrupted_at=time.time(),reason='Doubao historical native request was reinserted above baseline rowid and falsely rejected as an existing conversation. Fixed immutable pre-send message identity filter; recovered same original task 188 from two stable first-turn native reads, one click, no resend. Only two Doubao workers drained/reloaded. This window is not a 12h pass.')
atomic(oldroot/'interrupted_report.json',status);atomic(oldroot/'status.json',status)
start=time.time();test_id='question-only-soak12h-rowidfix-'+str(int(start));root=base/'soak'/test_id;root.mkdir(mode=0o700)
manifest.update(test_id=test_id,started_at=start,deadline=start+43200,supersedes=old['test_id'],
    window_baseline={model:lane(panel,model)['current'] for model in manifest['jobs']},
    historical_row_fix={'at':fix['at'],'original_task':fix['task_id'],'unknown_resends':0},
    scope=manifest['scope']+' Immutable historical message identity snapshot guards SQLite history replacement; existing CID with a genuinely new user request still fails closed. Same six original jobs, fresh 12h recorder only.')
for value in manifest['window_baseline'].values():value['verified_unique_receipts']=value['unique_processed']
manifest['docker_before']=subprocess.check_output(['docker','inspect',*manifest['containers'],'--format','{{.Name}} {{.State.StartedAt}}'],text=True).strip()
atomic(root/'manifest.json',manifest)
oldunit=old['service'].removesuffix('.service');unit='geo-'+test_id
when=datetime.fromtimestamp(math.ceil(manifest['deadline']),timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
for suffix in ['.service','-deadline.service','-deadline.timer']:
    source=(Path('/etc/systemd/system')/(oldunit+suffix)).read_text().replace(str(oldroot),str(root)).replace(oldunit,unit)
    if suffix.endswith('.timer'):source='\n'.join('OnCalendar='+when if line.startswith('OnCalendar=') else line for line in source.splitlines())+'\n'
    (Path('/etc/systemd/system')/(unit+suffix)).write_text(source)
value={**{key:manifest[key] for key in ('test_id','started_at','deadline','duration_seconds')},'root':str(root),'service':unit+'.service','deadline_timer':unit+'-deadline.timer'}
atomic(pointer,value);subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now',unit+'.service',unit+'-deadline.timer'],check=True)
print(json.dumps(value))

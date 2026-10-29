from datetime import datetime,timezone
import json
import math
from pathlib import Path
import subprocess
import sys
import time
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,atomic,lane,read
base=Path('/opt/monitor/geo-capture');pointer=base/'soak12h_current.json';old=read(pointer)
if '-fencefix-' in old['test_id']:print(json.dumps(old));raise SystemExit(0)
assert old['test_id']=='question-only-soak12h-retest-1792061584'
oldroot=Path(old['root']);manifest=read(oldroot/'manifest.json');status=read(oldroot/'status.json')
assert (base/'maintenance/20261015-unified/native-lease-upgrade/report.json').is_file()
api=API();panel=api.panel()
for model,job in manifest['jobs'].items():
    value=lane(panel,model)['current']
    assert value['batch']==job['batch'] and value['service_state'] in {'active','activating'} and not value['needs_review'],value
subprocess.run(['systemctl','disable','--now',old['service'],old['deadline_timer']],check=True)
status.update(status='interrupted',interrupted_at=time.time(),reason='Confirmed 58.87s web observation interval from pre-operation reservation timing; completion fence fixes it conservatively. Native 45s lease shorter than bounded75s preparation caused transient stale; drained/reloaded150s lease. Prior anomalies retained, this window is not a pass.')
atomic(oldroot/'interrupted_report.json',status);atomic(oldroot/'status.json',status)
start=time.time();test_id='question-only-soak12h-fencefix-'+str(int(start));root=base/'soak'/test_id;root.mkdir(mode=0o700)
manifest.update(test_id=test_id,started_at=start,deadline=start+43200,supersedes=old['test_id'],
    window_baseline={m:lane(panel,m)['current'] for m in manifest['jobs']},
    scope=manifest['scope']+' Completion-fence and native bounded-lease retest. Window interval metrics exclude historical starts; batch_min_send_interval preserves historical failure. Existing tasks/IDs intact.')
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
print(json.dumps(value))

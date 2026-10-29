"""Reset only the observation/deadline window after fixes; retain the same paid job."""
from datetime import datetime,timezone
import json
import math
from pathlib import Path
import subprocess
import sys
import time
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.soak import audit
from geo_source_cards.runtime import atomic_json
base=Path('/opt/monitor/geo-capture');pointer=base/'creation_soak_current.json';old=runtime.read(pointer)
roster_fix='--after-roster-fix' in sys.argv
if '-rosterfix-' in old['test_id'] or ('-retest-' in old['test_id'] and not roster_fix):print(json.dumps(old));raise SystemExit(0)
if roster_fix:assert old['test_id']=='creation-soak6h-retest-1792061692'
oldroot=Path(old['root']);manifest=runtime.read(oldroot/'manifest.json');status=runtime.read(oldroot/'status.json')
baseline={}
for identity in manifest['jobs']:
    proof=audit(runtime.job_root(identity))
    assert not proof['control'].get('paused') and not proof['unknown_calls']
    baseline[identity]=[a['id'] for a in proof['approved']]
subprocess.run(['systemctl','disable','--now',old['service'],old['deadline_timer']],check=True)
status.update(status='interrupted',interrupted_at=time.time(),reason=('Phantom product from generic feature bullet fixed in original engine parser; known delivered research repaired against same full original source contract. Same paid job retained; this short window is not a 6h pass.' if roster_fix else 'Transient read-only balance lookup and premature pause before original bounded repair fixed. Same paid job retained. This short window is not a 6h pass.'))
atomic_json(oldroot/'interrupted_report.json',status);atomic_json(oldroot/'status.json',status)
start=time.time();identity=('creation-soak6h-rosterfix-' if roster_fix else 'creation-soak6h-retest-')+str(int(start));root=base/'soak'/identity;root.mkdir(mode=0o700)
manifest.update(test_id=identity,started_at=start,deadline=start+21600,approved_before=baseline,supersedes=old['test_id'])
atomic_json(root/'manifest.json',manifest)
oldunit=old['service'].removesuffix('.service');unit='geo-'+identity
when=datetime.fromtimestamp(math.ceil(manifest['deadline']),timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
for suffix in ['.service','-deadline.service','-deadline.timer']:
    text=(Path('/etc/systemd/system')/(oldunit+suffix)).read_text().replace(str(oldroot),str(root)).replace(oldunit,unit)
    if suffix.endswith('.timer'):
        text='\n'.join('OnCalendar='+when if line.startswith('OnCalendar=') else line for line in text.splitlines())+'\n'
    (Path('/etc/systemd/system')/(unit+suffix)).write_text(text)
value={**{k:manifest[k] for k in ('test_id','started_at','deadline','duration_seconds','jobs')},'root':str(root),'service':unit+'.service','deadline_timer':unit+'-deadline.timer'}
atomic_json(pointer,value)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now',unit+'.service',unit+'-deadline.timer'],check=True)
print(json.dumps(value))

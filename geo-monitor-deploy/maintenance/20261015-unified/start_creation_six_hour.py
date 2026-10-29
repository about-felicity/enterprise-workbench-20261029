"""Start the authorized creation-only fixed queue + six-hour evidence recorder."""
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

base=Path('/opt/monitor/geo-capture');pointer=base/'creation_soak_current.json'
if pointer.exists():print(pointer.read_text());raise SystemExit(0)
acceptance=runtime.read(base/'maintenance/20261015-unified/creation-acceptance.json')
proof=audit(runtime.job_root(acceptance['result']['job_id']))
assert len(proof['approved'])==2 and proof['day']['status']=='complete'
atomic_json(base/'maintenance/20261015-unified/creation-acceptance-report.json',proof)
stamp=str(int(time.time()));test_id='creation-soak6h-'+stamp;root=base/'soak'/test_id
root.mkdir(mode=0o700);unit='geo-'+test_id
start=time.time()
result=runtime.action('new',{**acceptance['selected'],'max_per_category':10},'4dbd41eeb2be4ef5983040c389047eb2')
manifest={'test_id':test_id,'started_at':start,'deadline':start+21600,'duration_seconds':21600,
    'jobs':[result['job_id']],'acceptance_job':proof['job_id'],'settings':runtime.pipeline_control.settings(runtime.SHARED),
    'scope':'Fixed queue up to 10 per genre, only existing GEO fulltext. Shared original budget and quality checks unchanged. Production/idle times reported separately; no automatic repeated paid jobs.'}
atomic_json(root/'manifest.json',manifest)
python='/home/user/geo-editorial/venv/bin/python'
common='WorkingDirectory=/opt/monitor/geo-content\nEnvironment=PYTHONPATH=/opt/monitor/geo-content:/opt/monitor/geo-content/engine\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nUMask=0077\n'
service='[Unit]\nDescription=GEO actual creation six-hour audit\nAfter=geo-content-worker.service\n[Service]\nType=simple\n'+common+'ExecStart='+python+' -B -m creation.soak --root '+str(root)+'\nRestart=on-failure\nRestartSec=20\n[Install]\nWantedBy=multi-user.target\n'
deadline_service='[Unit]\nDescription=GEO creation test-owned drain deadline\n[Service]\nType=oneshot\n'+common+'ExecStart='+python+' -B -m creation.soak --root '+str(root)+' --deadline-only\n'
when=datetime.fromtimestamp(math.ceil(manifest['deadline']),timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
timer='[Unit]\nDescription=GEO creation six-hour independent deadline\n[Timer]\nOnCalendar='+when+'\nAccuracySec=1s\nPersistent=true\nUnit='+unit+'-deadline.service\n[Install]\nWantedBy=timers.target\n'
for suffix,text in [('.service',service),('-deadline.service',deadline_service),('-deadline.timer',timer)]:
    (Path('/etc/systemd/system')/(unit+suffix)).write_text(text)
value={**{k:manifest[k] for k in ('test_id','started_at','deadline','duration_seconds','jobs')},'root':str(root),'service':unit+'.service','deadline_timer':unit+'-deadline.timer'}
atomic_json(pointer,value)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now',unit+'.service',unit+'-deadline.timer'],check=True)
print(json.dumps(value))

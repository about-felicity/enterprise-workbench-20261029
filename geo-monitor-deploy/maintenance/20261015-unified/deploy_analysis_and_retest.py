"""Deploy proven display/cache fix, then retest same capture jobs without resends."""
import ast
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import atomic,read

base=Path('/opt/monitor/geo-capture');pointer=base/'soak12h_current.json'
release=base/'analysis_display_release.json'
if release.exists():print(release.read_text());raise SystemExit(0)
old=read(pointer);oldroot=Path(old['root']);manifest=read(oldroot/'manifest.json')
status=read(oldroot/'status.json')
assert status['status']=='running'
target=Path('/opt/monitor/doubao_dashboard_server.py');incoming=Path('/tmp/doubao_dashboard_server.creation.py')
ast.parse(incoming.read_text());stamp=str(int(time.time()));backup=base/'backups'/('analysis-display-'+stamp)
backup.mkdir(mode=0o700);shutil.copy2(target,backup/target.name)
before=subprocess.check_output(['docker','inspect','monitor-dashboard-api','--format','{{.State.StartedAt}}'],text=True).strip()
# Stop only observation/deadline for superseded test; collectors keep their exact jobs.
subprocess.run(['systemctl','disable','--now',old['deadline_timer'],old['service']],check=True)
status.update(status='interrupted',interrupted_at=time.time(),reason='Authorized analysis display/cache correction; existing capture jobs keep running. A fresh full 12h observation window follows; this shorter window is not a pass.')
atomic(oldroot/'interrupted_report.json',status);atomic(oldroot/'status.json',status)
temporary=target.with_suffix('.creation-new');shutil.copy2(incoming,temporary);shutil.copymode(target,temporary);temporary.replace(target)
subprocess.run(['docker','restart','monitor-dashboard-api'],check=True,capture_output=True)
ready=False
for _ in range(40):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8765/api/models',timeout=4) as stream:data=json.load(stream)
        ready=bool(data.get('models'))
        if ready:break
    except Exception:pass
    time.sleep(1)
if not ready:
    shutil.copy2(backup/target.name,target);subprocess.run(['docker','restart','monitor-dashboard-api'],check=True,capture_output=True)
    raise RuntimeError('API readiness failed; source restored. Inspect original recorder before resuming.')
after=subprocess.check_output(['docker','inspect','monitor-dashboard-api','--format','{{.State.StartedAt}}'],text=True).strip()
start=time.time();test_id='question-only-soak12h-retest-'+str(int(start));root=base/'soak'/test_id;root.mkdir(mode=0o700)
manifest.update(test_id=test_id,started_at=start,deadline=start+43200,duration_seconds=43200,
    window_baseline=status['models'],supersedes=old['test_id'],
    scope=manifest['scope']+' Retest after explicit analysis-only deployment; SAME capture batch IDs retained, no new questions or reset. Totals include pre-window batch observations; window_counts reports additions during this test.')
manifest['docker_before']=subprocess.check_output(['docker','inspect',*manifest['containers'],'--format','{{.Name}} {{.State.StartedAt}}'],text=True).strip()
atomic(root/'manifest.json',manifest)
unit='geo-'+test_id;python=str(base/'venv/bin/python');script=str(base/'all_channel_soak.py')
when=datetime.fromtimestamp(math.ceil(manifest['deadline']),timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
service=f'[Unit]\nDescription=GEO six-channel exact-question 12h retest\nAfter=network-online.target\n[Service]\nExecStart={python} -u {script} --root {root}\nRestart=on-failure\nRestartPreventExitStatus=2\nRestartSec=20\nUMask=0077\n[Install]\nWantedBy=multi-user.target\n'
deadline=f'[Unit]\nDescription=Drain only registered six capture test jobs\n[Service]\nType=oneshot\nExecStart={python} -u {script} --root {root} --pause-only\nRestart=on-failure\nRestartSec=20\nUMask=0077\n'
timer=f'[Unit]\nDescription=GEO 12h retest independent deadline\n[Timer]\nOnCalendar={when}\nAccuracySec=1s\nPersistent=true\nUnit={unit}-deadline.service\n[Install]\nWantedBy=timers.target\n'
for suffix,text in [('.service',service),('-deadline.service',deadline),('-deadline.timer',timer)]:
    (Path('/etc/systemd/system')/(unit+suffix)).write_text(text)
new={'test_id':test_id,'root':str(root),'service':unit+'.service','deadline_timer':unit+'-deadline.timer',
     'started_at':start,'deadline':manifest['deadline'],'duration_seconds':43200}
atomic(pointer,new)
record={'at':time.time(),'backup':str(backup),'source_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
        'api_restart_before':before,'api_restart_after':after,'capture_batches_unchanged':manifest['jobs'],
        'short_window_archived':old['test_id'],'retest':new}
atomic(release,record)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now',unit+'.service',unit+'-deadline.timer'],check=True)
print(json.dumps(record))

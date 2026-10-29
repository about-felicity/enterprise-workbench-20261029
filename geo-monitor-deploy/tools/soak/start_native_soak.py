"""Install and start only the new native two-hour test supervisor."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import fcntl
import json
from pathlib import Path
import shutil
import subprocess
import time
from datetime import datetime, timezone
from native_soak import API, BASE, MODELS, atomic, lane, read


def command(*args):
    return subprocess.run(args,capture_output=True,text=True,check=True,timeout=30).stdout.strip()


with (BASE/'native-soak-install.lock').open('w') as lock:
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    pointer=BASE/'native_soak_current.json'
    if pointer.exists():
        old=read(pointer)
        state=Path(old['root'])/'status.json'
        if not state.exists() or read(state)['status'] not in {'complete','needs_attention'}:
            print(json.dumps({'existing_test':old},ensure_ascii=False))
            raise SystemExit(0)
    api=API();panel=api.panel()
    for model in MODELS:
        value=lane(panel,model)
        if value['current']['state']!='complete' or value['current']['service_state']!='inactive':
            raise RuntimeError('Expected completed idle batch:'+model)
        if len(value['settings']['questions'])!=21 or value['settings']['interval']<30:
            raise RuntimeError('Unexpected native settings')
    start=time.time();test_id='doubao-soak2h-'+str(int(start))
    root=BASE/'soak'/test_id;root.mkdir(mode=0o700)
    manifest={'test_id':test_id,'started_at':start,'deadline':start+7200,'duration_seconds':7200,
              'original':{m:{k:lane(panel,m)[k] for k in ('settings','revision','current')} for m in MODELS},'jobs':{},
              'scope':'Two new native batches; 21 questions, 20-round capacity, original intervals; graceful pause after 7200 seconds'}
    atomic(root/'manifest.json',manifest)
    unit='geo-doubao-soak2h-'+str(int(start))
    python=str(BASE/'venv/bin/python');script=str(BASE/'native_soak.py')
    service=f'''[Unit]
Description=GEO two Doubao native two-hour capture soak
After=network-online.target geo-monitor-status.service
Wants=geo-monitor-status.service
StartLimitIntervalSec=0
[Service]
Type=simple
ExecStart={python} -u {script} --root {root}
Restart=on-failure
RestartSec=20
MemoryMax=256M
UMask=0077
[Install]
WantedBy=multi-user.target
'''
    deadline=datetime.fromtimestamp(manifest['deadline'],timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    pause_service=f'''[Unit]
Description=Graceful deadline pause for {test_id}
After=network-online.target
[Service]
Type=oneshot
ExecStart={python} -u {script} --root {root} --pause-only
Restart=on-failure
RestartSec=20
UMask=0077
'''
    timer=f'''[Unit]
Description=Two-hour native soak pause deadline
[Timer]
OnCalendar={deadline}
Persistent=true
AccuracySec=1s
Unit={unit}-deadline.service
[Install]
WantedBy=timers.target
'''
    destination=Path('/etc/systemd/system')
    for suffix,content in [('.service',service),('-deadline.service',pause_service),('-deadline.timer',timer)]:
        (destination/(unit+suffix)).write_text(content)
    command('systemctl','daemon-reload')
    atomic(pointer,{'test_id':test_id,'root':str(root),'service':unit+'.service','deadline_timer':unit+'-deadline.timer',
                    'started_at':start,'deadline':manifest['deadline']})
    command('systemctl','enable','--now',unit+'-deadline.timer')
    command('systemctl','enable','--now',unit+'.service')
    print(json.dumps(read(pointer),ensure_ascii=False))

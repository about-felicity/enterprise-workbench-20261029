"""Add the control UI and immutable job templates; keep captures running."""
from pathlib import Path
import json
import shutil
import subprocess
import time

BASE=Path('/opt/monitor/geo-capture')
PACKAGE=Path(__file__).parent
backup=BASE/'backups'/('control-panel-'+str(int(time.time())))
backup.mkdir(mode=0o700)
for name in ('fleet_status.py','capture_bridge.py','fleet.json'):
    shutil.copy2(BASE/name,backup/name)
native=Path('/home/user/redroid-doubao/geo-batch-code/geo_batch_bridge.py')
shutil.copy2(native,backup/'geo_batch_bridge.py')
for name in ('control_panel.py','login_probe.py','native_entry.py','panel.html','fleet_status.py','capture_bridge.py',
             'test_control_panel.py','test_capture_bridge.py'):
    target=BASE/name
    temporary=target.with_suffix('.panel-install')
    shutil.copy2(PACKAGE/name,temporary)
    temporary.chmod(0o644)
    temporary.replace(target)
temporary=native.with_suffix('.panel-install')
shutil.copy2(PACKAGE/'geo_batch_bridge.py',temporary)
temporary.chmod(0o644)
temporary.replace(native)
common='''Restart=on-failure
RestartPreventExitStatus=2
RestartSec=30
TimeoutStopSec=35
KillMode=mixed
UMask=0077
TasksMax=512
'''
web=f'''[Unit]
Description=GEO web capture batch %i
After=docker.service geo-monitor-status.service network-online.target
Wants=geo-monitor-status.service network-online.target
PartOf=geo-monitor.target
[Service]
User=user
WorkingDirectory={BASE}
Environment=PYTHONUNBUFFERED=1
ExecStart={BASE}/venv/bin/python -u {BASE}/capture_bridge.py --config {BASE}/panel/jobs/%i.json
MemoryHigh=1400M
MemoryMax=2200M
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths={BASE}
PrivateTmp=true
{common}
[Install]
WantedBy=geo-monitor.target
'''
native_unit=f'''[Unit]
Description=GEO native Doubao capture batch %i
After=docker.service network-online.target
Requires=docker.service
PartOf=geo-monitor.target
[Service]
User=root
WorkingDirectory=/home/user/redroid-doubao
Environment=PYTHONUNBUFFERED=1
ExecStart=/home/user/redroid-doubao/worker-venv/bin/python -u {BASE}/native_entry.py --config {BASE}/panel/jobs/%i.json
{common}
[Install]
WantedBy=geo-monitor.target
'''
for name,text in (('geo-web@.service',web),('geo-native@.service',native_unit)):
    path=Path('/etc/systemd/system')/name
    if path.exists():shutil.copy2(path,backup/name)
    path.write_text(text)
# Initialize the registry before switching HTTP service, preserving live batches.
import sys
sys.path.insert(0,str(BASE))
from control_panel import Controller
control=Controller(BASE)
control.all()
subprocess.run(['systemd-analyze','verify','/etc/systemd/system/geo-web@.service','/etc/systemd/system/geo-native@.service'],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
(BASE/'panel_deployment.json').write_text(json.dumps({'at':time.time(),'backup':str(backup),'templates':['geo-web@.service','geo-native@.service']},indent=2))
print(json.dumps({'status':'deployed','backup':str(backup),'url':'http://192.168.31.106:8803/'}))

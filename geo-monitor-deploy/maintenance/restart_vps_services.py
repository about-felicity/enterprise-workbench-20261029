"""Restart only GEO's existing public authentication/proxy services."""
import json
from pathlib import Path
import subprocess
from datetime import datetime,timezone,timedelta

BASE=Path('/opt/monitor/geo-capture/maintenance/20261015-reorganize')
UNITS=('nginx.service','geo-monitor-auth.service','monitor-offline-fallback.service')
SSH=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
    '-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72']
def remote(command):
    return subprocess.run(SSH+[command],capture_output=True,text=True,check=True,timeout=40).stdout.strip()
def snapshot():
    return remote('systemctl show '+' '.join(UNITS)+' -p Id -p MainPID -p ActiveState -p ExecMainStartTimestampMonotonic')
assert not (BASE/'vps-restart-started.json').exists(),'VPS restart already attempted; inspect actual state before retrying'
before=snapshot()
remote('/usr/sbin/nginx -t')
(BASE/'vps-restart-started.json').write_text(json.dumps({'before':before}),encoding='utf8')
remote('systemctl restart geo-monitor-auth.service monitor-offline-fallback.service')
remote('systemctl restart nginx.service')
after=snapshot()
assert after.count('ActiveState=active')==3
result={'at':datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds'),'before':before,'after':after,
    'nginx_configuration_validated':True,'credentials_and_session_secret_preserved':True}
data=json.dumps(result,ensure_ascii=False,indent=2)
(BASE/'vps-restart.json').write_text(data,encoding='utf8')
export=Path('/home/user/redroid-doubao/reorganization-20261015/vps-restart.json')
export.write_text(data,encoding='utf8');export.chmod(0o644)
print(data)

from pathlib import Path
import json,math,shutil,subprocess
from datetime import datetime,timezone
base=Path('/opt/monitor/geo-capture');p=json.loads((base/'all_channel_soak_current.json').read_text());root=Path(p['root'])
timer=Path('/etc/systemd/system')/p['deadline_timer']
backup=root/'diagnostics/deadline-timer-before-rounding.conf'
if not backup.exists():shutil.copy2(timer,backup)
lines=timer.read_text().splitlines();found=[i for i,l in enumerate(lines) if l.startswith('OnCalendar=')];assert len(found)==1
lines[found[0]]='OnCalendar='+datetime.fromtimestamp(math.ceil(p['deadline']),timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
timer.write_text('\n'.join(lines)+'\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart',p['deadline_timer']],check=True)
subprocess.run(['systemctl','restart',p['service']],check=True)
print(subprocess.check_output(['systemctl','show',p['deadline_timer'],'-p','ActiveState','-p','NextElapseUSecRealtime'],text=True))

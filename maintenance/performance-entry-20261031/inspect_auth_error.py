import shlex,subprocess
code=r'''
import subprocess
from pathlib import Path
print(subprocess.check_output(['systemctl','show','geo-monitor-auth','-p','User','-p','Group'],text=True))
text=subprocess.check_output(['journalctl','-u','geo-monitor-auth','-n','35','--no-pager'],text=True)
for line in text.splitlines():
 if any(t in line for t in ['Error','File "','Permission','Traceback','raise ']):print(line)
print('key_mode',oct(Path('/opt/geo-monitor-auth/performance-auth.key').stat().st_mode&0o777))
'''
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
subprocess.run(ssh+['python3 -c '+shlex.quote(code)],check=True)

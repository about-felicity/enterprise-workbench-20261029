import subprocess,shlex
code=r'''
import subprocess,json
from pathlib import Path
print(subprocess.run(['ps','-p','40906','-o','pid,ppid,lstart,args'],capture_output=True,text=True).stdout)
print('\n'.join(s for s in subprocess.run(['ss','-ntp'],capture_output=True,text=True).stdout.splitlines() if 'pid=40906,' in s))
print(subprocess.run(['journalctl','_PID=40906','-n','8','--no-pager'],capture_output=True,text=True).stdout)
print('\n'.join(s for s in Path('/etc/ssh/sshd_config').read_text().splitlines() if s.strip() and not s.strip().startswith('#') and any(k in s.lower() for k in ['include','match','clientalive','tcpkeep','gatewayports'])))
print('\n'.join(s for s in subprocess.run(['/usr/sbin/sshd','-T'],capture_output=True,text=True).stdout.splitlines() if s.startswith(('clientalive','tcpkeepalive','gatewayports'))))
'''
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=30);print(r.stdout);print(r.stderr)

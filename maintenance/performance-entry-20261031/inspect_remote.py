import subprocess,json,shlex
from pathlib import Path
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
code="""from pathlib import Path
p=Path('/opt/geo-monitor-auth/server.py');s=p.read_text();start=s.index('def verify(');end=s.index('def ',start+5);print(s[start:end]);start=s.index('    def do_GET');print(s[start:start+800])
s=Path('/etc/nginx/nginx.conf').read_text();i=s.index('location = /geo_monitor/_auth');print(s[i:i+700]);print('account_exists',any(x.split(':',1)[0]=='superadmin' for x in Path('/etc/nginx/.geo_monitor_htpasswd').read_text().splitlines()))
"""
subprocess.run(ssh+['python3 -c '+shlex.quote(code)],check=True)

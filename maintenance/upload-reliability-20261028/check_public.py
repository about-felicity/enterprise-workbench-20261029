import subprocess,shlex
code="""import json,re
from pathlib import Path
t=Path('/etc/nginx/nginx.conf').read_text();start=t.find('location ^~ /geo_monitor/api/geo-creation/')
print(json.dumps({'creation_block':t[start:t.find('}',start)+1] if start>=0 else 'missing','body_limits':re.findall(r'client_max_body_size[^;]*;',t),'oversize_errors':[s for s in Path('/var/log/nginx/error.log').read_text().splitlines() if 'too large body' in s and 'geo-creation' in s][-5:]}))"""
cmd=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=35);print(r.stdout);print(r.stderr);raise SystemExit(r.returncode)

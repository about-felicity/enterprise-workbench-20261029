import subprocess,shlex,json
from pathlib import Path
code="""import json,subprocess
from pathlib import Path
logs={}
for name in ['error.log','geo_monitor_access.log']:
 p=Path('/var/log/nginx')/name
 if p.exists():logs[name]=[s for s in p.read_text(errors='replace').splitlines() if 'geo-creation' in s][-18:]
print(json.dumps(logs))
"""
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=40);print(r.stdout);print(r.stderr)
print(subprocess.run(['journalctl','-u','geo-content-api','--since','10 minutes ago','-n','35','--no-pager'],capture_output=True,text=True).stdout)
print(subprocess.run(['docker','logs','--since','10m','--tail','40','monitor-dashboard'],capture_output=True,text=True).stderr[-5000:])

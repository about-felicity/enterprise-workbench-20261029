import subprocess,shlex
code="from pathlib import Path; t=Path('/etc/nginx/nginx.conf').read_text(); s=t.index('location ^~ /geo_monitor/api/geo-creation/'); print(t[s:t.index('}',s)+1]); s=t.index('location = /geo_monitor/_auth'); print(t[s:t.index('}',s)+1])"
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=30);print(r.stdout);print(r.stderr)

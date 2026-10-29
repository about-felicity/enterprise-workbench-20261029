import subprocess,json,re
ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-i','/etc/monitor-vps2-tunnel/id_ed25519','root@117.55.234.72']
r=subprocess.run(ssh+['grep -hE "DELETE.*(devices|employees)" /var/log/nginx/*access.log | tail -60'],capture_output=True,text=True,timeout=30)
# Only request time, method/path and status. Do not expose session/IP fields.
for line in r.stdout.splitlines():
 m=re.search(r'\[([^]]+)\].*?"(DELETE [^\"]+)"\s+(\d+)',line)
 if m:print(json.dumps({'time':m[1],'request':m[2],'status':m[3]}))
print('exit',r.returncode,'error',r.stderr[:300])

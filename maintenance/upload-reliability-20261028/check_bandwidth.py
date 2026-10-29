import subprocess,shlex
code=r"from pathlib import Path; import re; t=Path('/etc/nginx/nginx.conf').read_text(); print('\n'.join(s for s in t.splitlines() if any(x in s for x in ['limit_rate','limit_conn','limit_req','proxy_buffer','gzip']))); print('disk'); import shutil; print(shutil.disk_usage('/var/lib/nginx'))"
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=30);print(r.stdout);print(r.stderr)

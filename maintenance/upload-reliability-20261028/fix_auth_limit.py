import subprocess,shlex
code=r'''
import os,shutil,subprocess,json
from pathlib import Path
p=Path('/etc/nginx/nginx.conf');text=p.read_text()
start=text.index('location = /geo_monitor/_auth');end=text.index('}',start)+1
block=text[start:end]
assert 'internal;' in block and 'proxy_pass_request_body off;' in block
import re
if 'client_max_body_size' in block:
 newblock=re.sub(r'client_max_body_size\s+\S+;', 'client_max_body_size 8m;',block)
else:newblock=block.replace('internal;', 'internal;\n            client_max_body_size 8m;',1)
backup=Path('/root/geo-monitor-access-backups/upload-reliability-20261028/nginx.before-auth-limit.conf')
assert not backup.exists();shutil.copy2(p,backup)
tmp=p.with_suffix('.upload.tmp');tmp.write_text(text[:start]+newblock+text[end:]);tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p)
r=subprocess.run(['nginx','-t'],capture_output=True,text=True)
if r.returncode:
 shutil.copy2(backup,p);raise RuntimeError(r.stderr)
subprocess.run(['systemctl','reload','nginx'],check=True)
print(json.dumps({'auth_body_limit':'8m','authentication_preserved':True,'nginx_test':True}))
'''
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=45);print(r.stdout);print(r.stderr);raise SystemExit(r.returncode)

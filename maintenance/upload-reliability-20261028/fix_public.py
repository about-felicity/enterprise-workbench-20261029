import subprocess,shlex
code=r'''
import hashlib,json,os,shutil,subprocess
from pathlib import Path
p=Path('/etc/nginx/nginx.conf');text=p.read_text();start=text.index('location ^~ /geo_monitor/api/geo-creation/');end=text.index('}',start)+1
block=text[start:end];assert block.count('client_max_body_size 2m;')==1
new=text[:start]+block.replace('client_max_body_size 2m;','client_max_body_size 8m;')+text[end:]
backup=Path('/root/geo-monitor-access-backups/upload-reliability-20261028');backup.mkdir(parents=True,exist_ok=False);shutil.copy2(p,backup/'nginx.conf')
tmp=p.with_suffix('.upload.tmp');tmp.write_text(new);tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p)
r=subprocess.run(['nginx','-t'],capture_output=True,text=True)
if r.returncode:
 shutil.copy2(backup/'nginx.conf',p);raise RuntimeError(r.stderr)
subprocess.run(['systemctl','reload','nginx'],check=True)
print(json.dumps({'creation_body_limit':'8m','nginx_test':True,'backup':str(backup),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
'''
cmd=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(cmd,capture_output=True,text=True,timeout=45);print(r.stdout);print(r.stderr);raise SystemExit(r.returncode)

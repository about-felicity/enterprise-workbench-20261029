import hashlib,json,os,shutil,tarfile,subprocess,shlex
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/upload-reliability-20261028');root=Path('/opt/monitor/geo-content/creation')
release=json.loads((base/'release.json').read_text())
with tarfile.open('/tmp/upload-reliability-candidate.tar.gz') as tar:
 for name in ['uploads.js','library.js','panel.html']:
  p=root/name;row=next(r for r in release['files'] if r['server']==str(p))
  assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
  shutil.copy2(p,base/('before-slow-link-'+name))
  raw=tar.extractfile('creation/'+name).read();tmp=p.with_suffix('.slow.tmp');tmp.write_bytes(raw);tmp.chmod(0o644);os.replace(tmp,p)
  row['sha256']=hashlib.sha256(raw).hexdigest()
(base/'release.json').write_text(json.dumps(release,indent=2))
code=r'''
import subprocess,os,shutil,json
from pathlib import Path
p=Path('/etc/nginx/nginx.conf');t=p.read_text();s=t.index('location ^~ /geo_monitor/api/geo-creation/');e=t.index('}',s)+1;b=t[s:e]
assert 'proxy_read_timeout 90s;' in b and 'proxy_send_timeout 90s;' in b
n=b.replace('proxy_read_timeout 90s;','proxy_read_timeout 300s;').replace('proxy_send_timeout 90s;','proxy_send_timeout 300s;')
n=n.replace('proxy_cache off;', 'gzip on;\n            gzip_types application/json;\n            gzip_min_length 1024;\n            gzip_vary on;\n            proxy_cache off;')
back=Path('/root/geo-monitor-access-backups/upload-reliability-20261028/nginx.before-slow-link.conf');assert not back.exists();shutil.copy2(p,back)
tmp=p.with_suffix('.slow.tmp');tmp.write_text(t[:s]+n+t[e:]);tmp.chmod(p.stat().st_mode&0o777);os.replace(tmp,p)
r=subprocess.run(['nginx','-t'],capture_output=True,text=True)
if r.returncode:shutil.copy2(back,p);raise RuntimeError(r.stderr)
subprocess.run(['systemctl','reload','nginx'],check=True);print(json.dumps({'upload_wait_seconds':300,'json_gzip':True,'nginx_test':True}))
'''
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72','python3 -c '+shlex.quote(code)]
r=subprocess.run(args,capture_output=True,text=True,timeout=40);print(r.stdout);print(r.stderr);raise SystemExit(r.returncode)

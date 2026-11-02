"""Install restricted identity gateway; transfer secrets through encrypted SSH stdin."""
import base64,json,secrets,shlex,subprocess
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-entry-20261031');stage=work/'stage'
key=Path('/opt/monitor/secrets/performance-auth.key');key.parent.mkdir(parents=True,exist_ok=True)
if not key.exists():key.write_bytes(secrets.token_bytes(32))
key.chmod(0o600)
verifier=Path('/tmp/geo-performance-superadmin-20261031.verifier')
payload={'module':(stage/'auth/performance_access.py').read_text(),'key':base64.b64encode(key.read_bytes()).decode(),'verifier':verifier.read_text().strip()}
assert payload['verifier'].startswith('pbkdf2_sha256$600000$')
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72']
code=r'''
import ast,base64,json,shutil,subprocess,sys
from pathlib import Path
p=json.load(sys.stdin);work=Path('/opt/geo-monitor-auth/backups/performance-entry-20261031');work.mkdir(parents=True,exist_ok=True);work.chmod(0o700)
server=Path('/opt/geo-monitor-auth/server.py');nginx=Path('/etc/nginx/nginx.conf');users=Path('/etc/nginx/.geo_monitor_htpasswd')
for source in [server,nginx,users]:
 dest=work/source.name
 if not dest.exists():shutil.copy2(source,dest)
s=server.read_text()
if 'from performance_access import' not in s:
 s='from performance_access import respond as performance_respond, verify_password as verify_performance_password\n'+s
 old='    if digest.startswith("{SHA}"):'
 assert s.count(old)==1
 s=s.replace(old,'    if digest.startswith("pbkdf2_sha256$"):\n        return verify_performance_password(digest, password)\n'+old)
 old='        if parsed.path == "/auth":'
 assert s.count(old)==1
 s=s.replace(old,'        if parsed.path == "/auth/performance":\n            username = self.session_user()\n            if not username or username not in users():\n                self.send_response(401); self.end_headers(); return\n            performance_respond(self, username); return\n'+old)
ast.parse(s)
n=nginx.read_text()
block="""
        location = /geo_monitor/_performance_auth {
            internal;
            proxy_pass http://127.0.0.1:18766/auth/performance;
            proxy_pass_request_body off;
            proxy_set_header Content-Length "";
            proxy_set_header Cookie $http_cookie;
            proxy_set_header X-Real-IP $remote_addr;
        }
        location ^~ /geo_monitor/api/performance-entry/ {
            auth_request /geo_monitor/_performance_auth;
            auth_request_set $geo_performance_identity $upstream_http_x_geo_performance_identity;
            proxy_set_header X-Geo-Performance-Identity $geo_performance_identity;
            proxy_set_header Cookie $http_cookie;
            proxy_set_header Host $host;
            proxy_set_header X-Forwarded-Proto https;
            proxy_pass http://127.0.0.1:18765/api/performance-entry/;
            proxy_http_version 1.1;
            proxy_cache off;
            proxy_no_cache 1;
            proxy_cache_bypass 1;
            client_max_body_size 256k;
            proxy_connect_timeout 3s;
            proxy_read_timeout 30s;
        }
"""
if 'location = /geo_monitor/_performance_auth' not in n:
 anchor='        location = /geo_monitor/_auth {';assert n.count(anchor)==1;n=n.replace(anchor,block+anchor)
lines=users.read_text().splitlines();others=[x for x in lines if x.split(':',1)[0]!='superadmin'];updated='\n'.join(others+['superadmin:'+p['verifier']])+'\n'
try:
 Path('/opt/geo-monitor-auth/performance_access.py').write_text(p['module'])
 secret=Path('/opt/geo-monitor-auth/performance-auth.key');secret.write_bytes(base64.b64decode(p['key']));shutil.chown(secret,user='nginx',group='nginx');secret.chmod(0o600)
 server.write_text(s);users.write_text(updated);nginx.write_text(n)
 subprocess.run(['nginx','-t'],check=True,capture_output=True)
 subprocess.run(['systemctl','restart','geo-monitor-auth.service'],check=True)
 subprocess.run(['nginx','-s','reload'],check=True,capture_output=True)
 assert [x for x in users.read_text().splitlines() if x.split(':',1)[0]!='superadmin']==others
 print('GATEWAY_READY superadmin; other accounts preserved; private entry API cache disabled')
except Exception:
 for source in [server,nginx,users]:shutil.copy2(work/source.name,source)
 subprocess.run(['systemctl','restart','geo-monitor-auth.service']);subprocess.run(['nginx','-s','reload'],capture_output=True)
 raise
'''
subprocess.run(ssh+['python3 -c '+shlex.quote(code)],input=json.dumps(payload),text=True,check=True,timeout=60)
verifier.unlink()

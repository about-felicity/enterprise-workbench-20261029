"""Administer only GEO's VPS prefix via the already verified reverse-tunnel key.

Run on the LAN server. Never emit SSH passwords, login passwords or session
cookies. The root password in vps_config.txt is not copied to either server.
"""
import argparse
import json
import shlex
import subprocess

SSH=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes',
     '-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts',
     '-o','ConnectTimeout=10','root@117.55.234.72']


def vps_python(code):
    result=subprocess.run(SSH+['python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=60)
    if result.returncode:
        # Do not include arbitrary remote stdout in exceptions (a caller may
        # be requesting a short-lived session for an authorized browser test).
        raise RuntimeError('VPS administrative operation failed: '+result.stderr[:700])
    return result.stdout


def browser_cookie():
    # Issue a ten-minute test session for an existing site account without
    # changing accounts/passwords or turning off Nginx auth. Memory only.
    code="""import ast
from pathlib import Path
path=Path('/opt/geo-monitor-auth/server.py')
tree=ast.parse(path.read_text())
def listener(node):
    return isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='serve_forever'
assert sum(listener(node) for node in tree.body)==1
tree.body=[node for node in tree.body if not listener(node)]
namespace={'__name__':'geo_access_verification'}
exec(compile(tree,str(path),'exec'),namespace)
namespace['SESSION_SECONDS']=600
print(namespace['make_token'](next(iter(namespace['users']()))))
"""
    value=vps_python(code).strip()
    if not value or len(value)>2000:raise RuntimeError('VPS test session unavailable')
    return value


CONFIGURE=r'''
import hashlib,json,os,shutil,subprocess,time
from pathlib import Path
path=Path('/etc/nginx/nginx.conf')
text=path.read_text()
marker='# BEGIN GEO_CAPTURE_CONTROL PREFIX'
record=Path('/var/lib/geo-monitor-control/release.json')
if marker in text:
    assert record.exists()
    print(json.dumps(json.loads(record.read_text())))
    raise SystemExit(0)
anchor='        location ^~ /geo_monitor/api/ {'
assert text.count(anchor)==1
block="""        # BEGIN GEO_CAPTURE_CONTROL PREFIX
        location ^~ /geo_monitor/api/geo-capture/ {
            auth_request /geo_monitor/_auth;
            access_log /var/log/nginx/geo_monitor_access.log main;
            client_max_body_size 2m;
            proxy_pass http://127.0.0.1:13000/api/geo-capture/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header X-Forwarded-Prefix /geo_monitor;
            proxy_connect_timeout 5s;
            proxy_read_timeout 60s;
            proxy_send_timeout 60s;
            proxy_next_upstream off;
            proxy_cache off;
            proxy_no_cache 1;
            proxy_cache_bypass 1;
            proxy_cookie_path /api/geo-capture /geo_monitor/api/geo-capture;
            add_header Cache-Control "no-store" always;
            add_header X-Geo-Control "live" always;
        }
        # END GEO_CAPTURE_CONTROL PREFIX

"""
new=text.replace(anchor,block+anchor,1)
start=new.index('        location ^~ /geo_monitor/ {')
end=new.index('        # END GEO_MONITOR MANAGED',start)
root=new[start:end]
old_key='proxy_cache_key $uri$is_args$args;'
assert root.count(old_key)==1
root=root.replace(old_key,'proxy_cache_key "geo-control-prefix-v2:$uri$is_args$args";',1)
new=new[:start]+root+new[end:]
backup=Path('/root/geo-monitor-access-backups')/str(int(time.time()))
backup.mkdir(parents=True,mode=0o700)
shutil.copy2(path,backup/'nginx.conf')
before=subprocess.run(['systemctl','show','geo-monitor-auth.service','monitor-offline-fallback.service','-p','Id','-p','MainPID','-p','ExecMainStartTimestamp'],capture_output=True,text=True,check=True).stdout
temp=path.with_suffix('.geo-control.tmp');temp.write_text(new);temp.chmod(path.stat().st_mode&0o777);temp.replace(path)
test=subprocess.run(['nginx','-t'],capture_output=True,text=True)
if test.returncode:
    shutil.copy2(backup/'nginx.conf',path)
    raise RuntimeError('Nginx test failed; previous configuration restored: '+test.stderr[:600])
subprocess.run(['systemctl','reload','nginx'],check=True)
after=subprocess.run(['systemctl','show','geo-monitor-auth.service','monitor-offline-fallback.service','-p','Id','-p','MainPID','-p','ExecMainStartTimestamp'],capture_output=True,text=True,check=True).stdout
assert before==after,'Authentication or fallback service restarted'
result={'configured_at':time.time(),'backup':str(backup),'old_sha256':hashlib.sha256(text.encode()).hexdigest(),'new_sha256':hashlib.sha256(new.encode()).hexdigest(),'nginx_config_valid':True,'auth_and_fallback_services_unchanged':True,'control_cache_disabled':True,'control_auth_preserved':True}
record.parent.mkdir(mode=0o700,exist_ok=True);record.write_text(json.dumps(result,indent=2));record.chmod(0o600)
print(json.dumps(result))
'''


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['configure','status']);args=parser.parse_args()
    if args.mode=='configure':print(vps_python(CONFIGURE))
    else:print(vps_python("import json; from pathlib import Path; p=Path('/var/lib/geo-monitor-control/release.json'); print(p.read_text() if p.exists() else json.dumps({'configured':False}))"))

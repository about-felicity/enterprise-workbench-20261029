import json
import sys
sys.path.insert(0,'/opt/monitor/geo-capture')
from vps_geo_access import vps_python

code=r'''
import hashlib,json,shutil,subprocess,time
from pathlib import Path
path=Path('/etc/nginx/nginx.conf');text=path.read_text()
marker='# BEGIN GEO_CREATION_CONTROL PREFIX'
record=Path('/var/lib/geo-monitor-control/creation-release.json')
if marker in text:
    print(record.read_text());raise SystemExit(0)
anchor='        location ^~ /geo_monitor/api/ {'
assert text.count(anchor)==1
block="""        # BEGIN GEO_CREATION_CONTROL PREFIX
        location ^~ /geo_monitor/api/geo-creation/ {
            auth_request /geo_monitor/_auth;
            access_log /var/log/nginx/geo_monitor_access.log main;
            client_max_body_size 2m;
            proxy_pass http://127.0.0.1:13000/api/geo-creation/;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto https;
            proxy_set_header X-Forwarded-Prefix /geo_monitor;
            proxy_connect_timeout 5s;
            proxy_read_timeout 90s;
            proxy_send_timeout 90s;
            proxy_next_upstream off;
            proxy_cache off;
            proxy_no_cache 1;
            proxy_cache_bypass 1;
            add_header Cache-Control "no-store" always;
            add_header X-Geo-Creation "live" always;
        }
        # END GEO_CREATION_CONTROL PREFIX

"""
new=text.replace(anchor,block+anchor,1)
new=new.replace('geo-control-prefix-v2:$uri$is_args$args','geo-creation-prefix-v3:$uri$is_args$args')
backup=Path('/root/geo-monitor-access-backups')/('creation-'+str(int(time.time())))
backup.mkdir(parents=True,mode=0o700);shutil.copy2(path,backup/'nginx.conf')
before=subprocess.check_output(['systemctl','show','geo-monitor-auth.service','monitor-offline-fallback.service','-p','Id','-p','MainPID','-p','ExecMainStartTimestamp'],text=True)
path.write_text(new)
test=subprocess.run(['nginx','-t'],capture_output=True,text=True)
if test.returncode:
    shutil.copy2(backup/'nginx.conf',path);raise RuntimeError('Nginx test failed; restored prior configuration')
subprocess.run(['systemctl','reload','nginx'],check=True)
after=subprocess.check_output(['systemctl','show','geo-monitor-auth.service','monitor-offline-fallback.service','-p','Id','-p','MainPID','-p','ExecMainStartTimestamp'],text=True)
assert before==after
value={'configured_at':time.time(),'backup':str(backup),'auth_preserved':True,'cache_disabled':True,'nginx_valid':True,'auth_fallback_unchanged':True}
record.write_text(json.dumps(value,indent=2));record.chmod(0o600)
print(json.dumps(value))
'''
print(vps_python(code))

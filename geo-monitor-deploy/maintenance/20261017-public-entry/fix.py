"""Disable stale caching only for GEO frontend, preserving authentication and upstreams."""
import json,sys
sys.path.insert(0,'/tmp')
from vps_geo_access import vps_python
code=r'''
import hashlib,json,shutil,subprocess,time
from pathlib import Path
path=Path('/etc/nginx/nginx.conf');old=path.read_text()
start=old.index('        location ^~ /geo_monitor/ {');end=old.index('        # END GEO_MONITOR MANAGED',start)
block=old[start:end]
assert block.count('proxy_cache geo_monitor_frontend;')==1,'Inspect existing frontend cache configuration'
assert 'auth_request /geo_monitor/_auth;' in block and 'proxy_pass http://monitor_live_frontend/;' in block
replacement=block.replace('proxy_cache geo_monitor_frontend;','proxy_cache off; # GEO HTML must track the live frontend release')
replacement=replacement.replace('            add_header X-Content-Type-Options', '            add_header X-GEO-Frontend "live-no-shared-cache" always;\n            add_header X-Content-Type-Options')
new=old[:start]+replacement+old[end:]
folder=Path('/root/geo-monitor-access-backups')/('20261017-frontend-cache-'+str(int(time.time())));folder.mkdir(mode=0o700)
shutil.copy2(path,folder/'nginx.conf')
path.write_text(new)
try:
 subprocess.run(['/usr/sbin/nginx','-t'],capture_output=True,check=True)
 subprocess.run(['systemctl','reload','nginx'],capture_output=True,check=True)
except Exception:
 shutil.copy2(folder/'nginx.conf',path);subprocess.run(['/usr/sbin/nginx','-t'],capture_output=True,check=True);raise
result={'at':time.time(),'backup':str(folder),'old_sha256':hashlib.sha256(old.encode()).hexdigest(),'new_sha256':hashlib.sha256(new.encode()).hexdigest(),'auth_unchanged':True,'api_caches_unchanged':True,'frontend_proxy_cache':'off','reload_only':True}
(folder/'release.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
'''
print(vps_python(code))

"""Refresh only transient host resolution caches; preserve account and chat data."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,os,shutil,time
from pathlib import Path
os.umask(0o077)
name='doubao-hpe14-account2'
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/files'
backup=Path('/home/user/redroid-doubao/account2')/('network-cache-backup-'+str(int(time.time())))
backup.mkdir(mode=0o700)
subprocess.run(['docker','exec',name,'am','force-stop','com.larus.nova'],check=True)
for filename in ('hostcache_v1','hostcache_sync_v1'):
    p=root/filename
    if p.is_file():
        shutil.copy2(p,backup/filename)
        p.unlink()
        print('Saved and cleared',filename)
subprocess.run(['docker','exec',name,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)
print('Network cache backup',backup)

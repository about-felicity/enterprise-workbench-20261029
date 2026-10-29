"""Precreate distinct Keva files to prevent long generated paths colliding."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import os,subprocess,json,time,shutil
from pathlib import Path
from active_database_accounts import current_uid
os.umask(0o077)
name='doubao-hpe14-account2'
assert current_uid(name).endswith('066524')
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/files/keva/repo'
dirs=[d for d in root.glob('FlowIMSDKconversation-local-manager*') if len(d.name)==111]
assert len(dirs)==1
d=dirs[0]; st=d.stat(); entries=list(d.iterdir())
assert len(entries)==1 and len(entries[0].name)==100
subprocess.run(['docker','exec',name,'am','force-stop','com.larus.nova'],check=True)
backup=Path('/home/user/redroid-doubao/account2')/('keva-collision-backup-'+str(int(time.time())))
backup.mkdir(mode=0o700)
shutil.copytree(d,backup/'original')
for p in entries: p.rename(backup/p.name)
for suffix in ('.blk','.chk'):
    p=d/(d.name+suffix);p.touch(mode=0o600);os.chown(p,st.st_uid,st.st_gid)
print('Original collided file backed up at',backup,flush=True)
subprocess.run(['docker','exec',name,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)

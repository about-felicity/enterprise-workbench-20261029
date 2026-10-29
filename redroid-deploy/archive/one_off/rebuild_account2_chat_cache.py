"""Rebuild only current account's broken IM cache; preserve login and backups."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import os,sys,subprocess,json,sqlite3,time,shutil
from pathlib import Path
from active_database_accounts import current_uid
os.umask(0o077)
name='doubao-hpe14-account2';uid=current_uid(name)
assert uid.endswith('066524'),'Current account changed; do not touch it'
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/databases'
db=root/('im_database_'+uid)
with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as c:
    assert c.execute('select count(*) from im_conversation').fetchone()[0]==0,'Conversations exist; reassess diagnosis'
    row=c.execute('select message_id,server_index from im_message where local_message_id=?',('c10c6d72-e1be-4776-a36c-de9f25144bf8',)).fetchone()
    assert row is not None and row[0] is None and row[1]==0
subprocess.run(['docker','exec',name,'am','force-stop','com.larus.nova'],check=True)
backup=Path('/home/user/redroid-doubao/account2')/('im-cache-before-rebuild-'+str(int(time.time())))
backup.mkdir(mode=0o700)
for suffix in ('','-wal','-shm','-journal'):
    p=Path(str(db)+suffix)
    if p.exists():shutil.move(str(p),str(backup/p.name))
print('Original chat cache preserved at',backup,flush=True)
subprocess.run(['docker','exec',name,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)

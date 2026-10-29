"""Back up second emulator's IM-only synchronization state; preserve authentication."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import os,subprocess,json,time,shutil,sqlite3
from pathlib import Path
from active_database_accounts import current_uid
os.umask(0o077)
name='doubao-hpe14-account2';uid=current_uid(name)
assert uid.endswith('066524')
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova'
db=root/'databases'/('im_database_'+uid)
with sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True) as c:
    assert c.execute('select count(*) from im_conversation').fetchone()[0]==0
repo=root/'files/keva/repo'
targets=[repo/('FlowIMSDKCMD_'+uid+'_1'),repo/'FlowIMSDKmessage-interval-cache',repo/'FlowIMSDKomni_im_default_repo']
targets+=list(repo.glob('FlowIMSDKconversation-local-manager*'))
targets+=[repo/'default/launch_cache_conversation_info.sgv']
targets+=[Path(str(db)+s) for s in ('','-wal','-shm','-journal')]
assert not (repo/'FlowIMSDKomni_im_default_repo/token_seq_id_cache.sgv').exists(), 'Keep token cache, reassess before mutation'
subprocess.run(['docker','exec',name,'am','force-stop','com.larus.nova'],check=True)
backup=Path('/home/user/redroid-doubao/account2')/('im-sync-backup-'+str(int(time.time())))
backup.mkdir(mode=0o700)
for p in targets:
    if p.exists():
        dest=backup/p.relative_to(root);dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(p),str(dest))
print('IM sync backup',backup,flush=True)
subprocess.run(['docker','exec',name,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)

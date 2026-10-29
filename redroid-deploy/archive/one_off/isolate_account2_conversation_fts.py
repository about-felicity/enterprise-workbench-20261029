"""Reversible isolation of only legacy FTS triggers blocking native conversation writes."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from pathlib import Path
import os,json,subprocess,sqlite3,time,sys
from active_database_accounts import current_uid
os.umask(0o077)
c='doubao-hpe14-account2';uid=current_uid(c)
assert uid.endswith('066524')
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
info=json.loads(subprocess.check_output(['docker','inspect',c]))[0]
app=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova'
path=app/'databases'/('im_database_'+uid)
backup=Path('/home/user/redroid-doubao/account2')/('conversation-fts-isolation-'+str(int(time.time())))
backup.mkdir(mode=0o700)
if '--live' not in sys.argv:
 subprocess.run(['docker','exec',c,'am','force-stop','com.larus.nova'],check=True)
db=sqlite3.connect(path)
assert db.execute('select count(*) from im_conversation').fetchone()[0]==0
triggers=list(db.execute("select name,sql from sqlite_master where type='trigger' and tbl_name='im_conversation'"))
assert len(triggers)==4 and all(name.startswith('room_fts_content_sync_fts_im_conversation_') and 'fts_im_conversation' in sql for name,sql in triggers)
with sqlite3.connect(backup/'database-before.sqlite') as dest:db.backup(dest)
(backup/'restore-triggers.sql').write_text(';\n'.join(sql for _,sql in triggers)+';\n')
with db:
    for name,_ in triggers:db.execute('DROP TRIGGER "'+name+'"')
columns=[r[1] for r in db.execute('pragma table_info(im_conversation)')]
db.execute('EXPLAIN INSERT OR REPLACE INTO im_conversation('+','.join(columns)+') VALUES('+','.join('?' for _ in columns)+')',[None]*len(columns)).fetchall()
assert db.execute('pragma quick_check').fetchone()[0]=='ok'
db.close()
print('Only four conversation FTS triggers isolated; INSERT now compiles; rollback:',backup,flush=True)
if '--live' not in sys.argv:
 subprocess.run(['docker','exec',c,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)

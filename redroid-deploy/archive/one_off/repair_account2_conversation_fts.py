"""Backed-up migration of legacy mmicu FTS to native-compatible unicode61."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,sqlite3,time,os
from pathlib import Path
from active_database_accounts import current_uid
os.umask(0o077)
c='doubao-hpe14-account2';uid=current_uid(c)
assert uid.endswith('066524')
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
info=json.loads(subprocess.check_output(['docker','inspect',c]))[0]
app=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova'
path=app/'databases'/('im_database_'+uid)
backup=Path('/home/user/redroid-doubao/account2')/('conversation-fts-repair-'+str(int(time.time())))
backup.mkdir(mode=0o700)
subprocess.run(['docker','exec',c,'am','force-stop','com.larus.nova'],check=True)
db=sqlite3.connect(path)
assert db.execute('select count(*) from im_conversation').fetchone()[0]>=1
oldsql=db.execute("select sql from sqlite_master where name='fts_im_conversation'").fetchone()[0]
assert 'tokenize = mmicu' in oldsql
assert db.execute("select count(*) from sqlite_master where type='trigger' and tbl_name='im_conversation'").fetchone()[0]==0
with sqlite3.connect(backup/'database-before.sqlite') as dest:db.backup(dest)
# Temporary alias only lets this repair connection open/drop the old empty
# virtual index; the resulting database uses built-in unicode61 explicitly.
tokenizer=db.execute("select fts3_tokenizer('unicode61')").fetchone()[0]
db.execute('select fts3_tokenizer(?,?)',('mmicu',tokenizer))
restore=Path('/home/user/redroid-doubao/account2/conversation-fts-isolation-1791962284/restore-triggers.sql').read_text()
(backup/'old-fts-schema.sql').write_text(oldsql+';\n'+restore)
with db:
    db.execute('drop table fts_im_conversation')
    db.execute(oldsql.replace('tokenize = mmicu','tokenize = unicode61'))
    db.execute("INSERT INTO fts_im_conversation(fts_im_conversation) VALUES('rebuild')")
# executescript is deliberately outside the index transaction, restores only
# the four reviewed trigger definitions saved before isolation.
db.executescript(restore)
assert db.execute("select count(*) from sqlite_master where type='trigger' and tbl_name='im_conversation'").fetchone()[0]==4
assert db.execute('pragma quick_check').fetchone()[0]=='ok'
print('Native-compatible conversation FTS installed; four triggers restored; indexed rows',db.execute('select count(*) from fts_im_conversation').fetchone()[0],'; backup',backup,flush=True)
db.close()
subprocess.run(['docker','exec',c,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)

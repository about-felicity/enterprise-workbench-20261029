"""Repair the now-confirmed native conversation FTS fault in account1."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import os,json,subprocess,sqlite3,time
from pathlib import Path
from active_database_accounts import current_uid
os.umask(0o077)
c='doubao-hpe14-13-test';uid=current_uid(c)
assert uid.endswith('385833')
assert subprocess.run(['systemctl','is-active','redroid-geo-products.service'],capture_output=True,text=True).stdout.strip() in ('failed','inactive')
info=json.loads(subprocess.check_output(['docker','inspect',c]))[0]
app=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova'
backup=Path('/home/user/redroid-doubao')/('account1-fts-repair-'+str(int(time.time())))
backup.mkdir(mode=0o700)
subprocess.run(['docker','exec',c,'am','force-stop','com.larus.nova'],check=True)
db=sqlite3.connect(app/'databases'/('im_database_'+uid))
sql=db.execute("select sql from sqlite_master where name='fts_im_conversation'").fetchone()[0]
assert 'tokenize = mmicu' in sql
triggers=list(db.execute("select name,sql from sqlite_master where type='trigger' and tbl_name='im_conversation'"))
assert len(triggers)==4
before=db.execute('select count(*) from im_message').fetchone()[0]
with sqlite3.connect(backup/'native-database-before.sqlite') as dest:db.backup(dest)
queue=Path('/home/user/redroid-doubao/batches/geo-products-21x5-account1-20261014/tasks.sqlite')
with sqlite3.connect(queue) as q,sqlite3.connect(backup/'queue-before.sqlite') as dest:q.backup(dest)
(backup/'original-fts.sql').write_text(sql+';\n'+';\n'.join(s for _,s in triggers)+';\n')
tokenizer=db.execute("select fts3_tokenizer('unicode61')").fetchone()[0]
db.execute('select fts3_tokenizer(?,?)',('mmicu',tokenizer))
with db:
 for name,_ in triggers:db.execute('DROP TRIGGER "'+name+'"')
 db.execute('DROP TABLE fts_im_conversation')
 db.execute(sql.replace('tokenize = mmicu','tokenize = unicode61'))
 db.execute("INSERT INTO fts_im_conversation(fts_im_conversation) VALUES('rebuild')")
db.executescript(';\n'.join(s for _,s in triggers)+';\n')
assert db.execute('select count(*) from im_message').fetchone()[0]==before
assert db.execute('pragma quick_check').fetchone()[0]=='ok'
db.close()
print('Account1 FTS repaired; four triggers and all messages preserved; backup:',backup,flush=True)
subprocess.run(['docker','exec',c,'am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)

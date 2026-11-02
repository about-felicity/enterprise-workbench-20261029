import subprocess,json,re,sqlite3,time,shutil
from pathlib import Path
for c in ['doubao-hpe14-account3','doubao-hpe14-account4']:
 pid=subprocess.check_output(['docker','exec',c,'pidof','com.larus.nova'],text=True).strip();fds=subprocess.check_output(['docker','exec',c,'ls','-l','/proc/'+pid+'/fd'],text=True)
 ids=set(re.findall(r'/im_database_(\d+)(?:-wal|-shm)?(?:\s|$)',fds));assert len(ids)==1;uid=ids.pop()
 info=json.loads(subprocess.check_output(['docker','inspect',c],text=True))[0];mount=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))
 p=mount/'data/com.larus.nova/databases'/('im_database_'+uid)
 w=Path('/home/user/redroid-doubao/expansion-20261102')/c;w.mkdir(exist_ok=True)
 subprocess.run(['docker','exec',c,'am','force-stop','com.larus.nova'],check=True)
 with sqlite3.connect(p) as db:
  sql=db.execute("select sql from sqlite_master where name='fts_im_conversation'").fetchone()[0]
  triggers=db.execute("select name,sql from sqlite_master where type='trigger' and tbl_name='im_conversation' order by name").fetchall();assert len(triggers)==4
  if 'mmicu' in sql:
   with sqlite3.connect(w/'before-fts.sqlite') as out:db.backup(out)
   tokenizer=db.execute("select fts3_tokenizer('unicode61')").fetchone()[0];db.execute('select fts3_tokenizer(?,?)',('mmicu',tokenizer))
   with db:
    db.execute('drop table fts_im_conversation');db.execute(sql.replace('tokenize = mmicu','tokenize = unicode61'));db.execute("INSERT INTO fts_im_conversation(fts_im_conversation) VALUES('rebuild')")
   assert db.execute("select name,sql from sqlite_master where type='trigger' and tbl_name='im_conversation' order by name").fetchall()==triggers
  assert db.execute('pragma quick_check').fetchone()[0]=='ok'
 print('FTS_VERIFIED',c,flush=True)
 subprocess.run(['docker','exec',c,'am','start','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'],check=True)

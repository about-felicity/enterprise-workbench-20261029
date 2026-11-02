import subprocess,json,re,sqlite3
from pathlib import Path
uids=[]
for c in ['doubao-hpe14-13-test','doubao-hpe14-account2','doubao-hpe14-account3','doubao-hpe14-account4']:
 pid=subprocess.check_output(['docker','exec',c,'pidof','com.larus.nova'],text=True).strip()
 fds=subprocess.check_output(['docker','exec',c,'ls','-l','/proc/'+pid+'/fd'],text=True)
 ids=set(re.findall(r'/im_database_(\d+)(?:-wal|-shm)?(?:\s|$)',fds));assert len(ids)==1,c
 uid=ids.pop();uids.append(uid)
 info=json.loads(subprocess.check_output(['docker','inspect',c],text=True))[0]
 dbpath=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/databases'/('im_database_'+uid)
 with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
  print(c,'uid_tail',uid[-4:],'fts',db.execute("select sql from sqlite_master where name='fts_im_conversation'").fetchone(),'triggers',db.execute("select name from sqlite_master where type='trigger' and tbl_name='im_conversation'").fetchall(),flush=True)
print('ALL_UNIQUE',len(uids)==len(set(uids)),flush=True)
print('CAPTURE_ROOT',subprocess.run(['find','/opt/monitor/geo-capture','-maxdepth','2','-type','f','-name','*.py'],capture_output=True,text=True).stdout[:4000])

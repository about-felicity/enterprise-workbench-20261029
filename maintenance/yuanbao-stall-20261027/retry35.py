import json,sqlite3,subprocess,sys,time,shutil
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code']
from native_client import NativeClient
from history_refresh import original_pair_matches
from native_core import enum
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261027-090005-e7c7269a');unit='geo-native@'+R.name+'.service'
subprocess.run(['systemctl','stop',unit],check=True,timeout=40)
try:
 db=sqlite3.connect(R/'tasks.sqlite');db.row_factory=sqlite3.Row;t=dict(db.execute('select * from tasks where ordinal=35').fetchone());tid=t['task_id']
 assert t['state']=='prepared' and t['capture_retries']==0 and t['request_id']=='d32b0dda1a7e85e3610ae5892062867f'
 binding=json.loads((R/(tid+'.binding.json')).read_text());c=NativeClient(R);c.connect()
 native=c.script.exports_sync.read_known(binding['conversation_id'],binding['server_answer_id']);c.close()
 assert original_pair_matches(binding,t,native)
 assert enum(native['message']['state'])==enum(native['content']['state'])=='INTERRUPTED'
 assert native['conversation']['isBusy'] is False and native['content']['isEof'] is False
 history=json.loads((R/(tid+'.history-refresh.json')).read_text())
 assert history.get('attempts',0)>=1 and history.get('proof',{}).get('request_id')==t['request_id']
 assert time.time()-t['prepared_at']>900
 archive=R/'failed-attempt-evidence'/(tid+'-0');archive.mkdir(parents=True,exist_ok=False)
 with sqlite3.connect(archive/'tasks-before.sqlite') as backup:db.backup(backup)
 (archive/'confirmed-interrupted.json').write_text(json.dumps(native,ensure_ascii=False))
 files=list(R.glob(tid+'.*'))
 for path in files:shutil.copy2(path,archive/path.name)
 for path in files:path.unlink()
 with db:
  db.execute('insert into failed_attempts values(?,?,?,?,?,?,?,?)',(tid,0,t['wire_question'],t['request_id'],binding['server_answer_id'],json.dumps(native,ensure_ascii=False),'operator_confirmed_interrupted_after_readback_attempt',time.time()))
  db.execute("update tasks set state='pending',capture_retries=1,not_before=?,attempts=0,prepared_at=null,request_id=null,answer_id=null,result_json=null,error=null where task_id=?",(time.time(),tid))
  db.execute('insert into events(task_id,time,event,detail) values(?,?,?,?)',(tid,time.time(),'operator_interrupted_send_recovery_scheduled',json.dumps({'old_request':t['request_id'],'same_question':True,'retry_limit':1,'evidence':str(archive)})))
 print('Confirmed interrupted request archived; original task scheduled for one retry')
finally:subprocess.run(['systemctl','start',unit],check=True)

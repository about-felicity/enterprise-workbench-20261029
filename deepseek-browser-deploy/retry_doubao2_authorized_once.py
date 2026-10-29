"""One authorized recovery of the exact unresolved task. Not a recurring installer."""
import sys,json,sqlite3,time,subprocess,fcntl
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_core import Queue
from question_only_adapters import DoubaoReader
batch='geo-panel-doubao2-20261019-090003-88e4f45b';root=Path('/home/user/redroid-doubao/batches')/batch
service='geo-native@'+batch+'.service'
subprocess.run(['systemctl','stop','geo-daily-control.service'],check=True)
try:
 subprocess.run(['systemctl','stop',service],check=True,timeout=50)
 with (Path('/run/lock/redroid-doubao-doubao-hpe14-account2.lock')).open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  q=Queue(root/'tasks.sqlite');t=dict(q.db.execute('select * from tasks where ordinal=13').fetchone())
  assert t['task_id']=='1188d66f-eb41-529f-89a6-5d34ea3e6a3c' and t['state']=='prepared' and t['capture_retries']==0
  assert t['wire_question']==t['question'] and t['request_id'] is None
  observed=DoubaoReader(root,'doubao-hpe14-account2').lookup(t)
  assert observed['status']=='absent','Original result appeared; preserve it instead of retrying'
  assert not q.db.execute("select 1 from events where task_id=? and event='operator_interrupted_send_recovery_scheduled'",(t['task_id'],)).fetchone()
  backup=root/('before-user-authorized-retry-'+str(int(time.time()))+'.sqlite')
  with sqlite3.connect(backup) as dest:q.db.backup(dest)
  audit={'authorized_by':'human reply in current chat 2026-10-19','scope':'exact ordinal13 once','original_send_unknown':True,'old_prepared_at':t['prepared_at'],'old_attempt':0,'original_question_unchanged':True,'lookup_before_retry':'absent'}
  with q.db:
   q.db.execute('insert into failed_attempts values(?,?,?,?,?,?,?,?)',(t['task_id'],0,t['wire_question'],None,None,json.dumps(audit),'user_authorized_unknown_send_retry',time.time()))
   q.db.execute("update tasks set state='pending',capture_retries=1,prepared_at=null,request_id=null,not_before=0,error=null where task_id=?",(t['task_id'],))
   q.event(t['task_id'],'operator_interrupted_send_recovery_scheduled',json.dumps(audit))
  q.db.close()
 print(json.dumps({'authorized_retry_scheduled':True,'batch':batch,'ordinal':13,'backup':str(backup)}),flush=True)
 subprocess.run(['systemctl','start',service],check=True)
finally:
 subprocess.run(['systemctl','start','geo-daily-control.service'],check=True)

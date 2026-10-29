"""Guarded recovery of only the observed account1/14 and account2/68 blockers."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,sqlite3,time,uuid,subprocess,os
from pathlib import Path
os.umask(0o077)
base=Path('/home/user/redroid-doubao');sys.path.insert(0,str(base/'geo-batch-code'))
from unattended_core import Queue,lookup,is_transient_error
from unattended_worker import databases
from active_database_accounts import current_uid
specs=[('doubao-hpe14-13-test','geo-products-21x5-account1-20261014','redroid-geo-products.service',14,'385833'),('doubao-hpe14-account2','geo-products-21x5-account2-relogin-20261013','redroid-geo-products-account2.service',68,'066524')]
for c,batch,service,ordinal,tail in specs:
 assert subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
 assert current_uid(c).endswith(tail)
 root=base/'batches'/batch;q=Queue(root/'tasks.sqlite')
 t=dict(q.db.execute('select * from tasks where ordinal=?',(ordinal,)).fetchone())
 assert t['state']=='needs_attention' and t['capture_retries']==0
 r=lookup(databases(c),t)
 with sqlite3.connect(root/('before-pause-reconcile-'+str(int(time.time()))+'.sqlite')) as dest:q.db.backup(dest)
 if ordinal==68:
  assert t['request_id']=='65d4721c-ef5f-4f39-8eb2-cb2ffa05f5b5' and is_transient_error(r)
  delay=q.schedule_transient_retry(t['task_id'],r)
  print('Account2 confirmed error archived; bounded retry scheduled with',delay,'seconds backoff',flush=True)
 else:
  assert t['task_id']=='0229008d-f689-5054-865f-8b0ebe73bf88' and t['request_id'] is None and r['status']=='absent'
  assert t['error']=='Send/answer is unresolved; no automatic resend'
  assert not q.db.execute("select 1 from events where task_id=? and event='operator_storage_recovery_scheduled'",(t['task_id'],)).fetchone()
  # This is an explicit operator recovery after the confirmed FTS/storage fix,
  # never a policy for automatically retrying an uncertain send.
  marker=str(uuid.uuid5(uuid.UUID(t['task_id']),'operator-storage-recovery:1'))
  audit={'native_request':'absent_after_restart_and_sync','server_ack':None,'reason':'Native conversation INSERT failed through mmicu FTS; unicode61 repair and restart completed; operator-authorized one controlled recovery; original click evidence retained'}
  with q.db:
   q.db.execute('insert into failed_attempts values(?,?,?,?,?,?,?,?)',(t['task_id'],0,t['wire_question'],None,None,json.dumps(audit),'operator_storage_failure_recovery',time.time()))
   q.db.execute("update tasks set state='pending',wire_question=?,capture_retries=1,not_before=0,attempts=0,prepared_at=null,request_id=null,error=null where task_id=?",(t['base_wire_question']+'\n（本次采集尝试编号：'+marker+'）',t['task_id']))
   q.event(t['task_id'],'operator_storage_recovery_scheduled',json.dumps(audit))
  print('Account1 storage failure archived; one distinct, guarded recovery attempt scheduled',flush=True)
 q.db.close()
for _,_,service,_,_ in specs:
 subprocess.run(['systemctl','reset-failed',service],check=True)
 subprocess.run(['systemctl','start',service],check=True)
print('Both services resumed with 45-second pacing, 900-second answer wait and bounded transient recovery',flush=True)

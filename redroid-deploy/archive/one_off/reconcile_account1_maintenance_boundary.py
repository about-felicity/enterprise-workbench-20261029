"""Operator reconciliation of the single send interrupted by Keva maintenance."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,subprocess,json,sqlite3,time,os,uuid,shutil
from pathlib import Path
os.umask(0o077);base=Path('/home/user/redroid-doubao')
sys.path.insert(0,str(base/'geo-batch-code'))
from unattended_core import Queue,lookup
from unattended_worker import databases
from active_database_accounts import current_uid
c='doubao-hpe14-13-test';service='redroid-geo-products.service'
assert current_uid(c).endswith('385833')
root=base/'batches/geo-products-21x5-account1-20261014';q=Queue(root/'tasks.sqlite')
t=dict(q.db.execute('select * from tasks where ordinal=21').fetchone())
assert t['state']=='prepared' and t['request_id'] is None and t['capture_retries']==0
assert lookup(databases(c),t)['status']=='absent'
assert not q.db.execute("select 1 from events where task_id=? and event='send_tap_returned'",(t['task_id'],)).fetchone()
assert time.time()-t['prepared_at']>180
subprocess.run(['systemctl','stop',service],check=True)
assert lookup(databases(c),t)['status']=='absent'
backup=root/('before-maintenance-boundary-recovery-'+str(int(time.time()))+'.sqlite')
with sqlite3.connect(backup) as dest:q.db.backup(dest)
marker=str(uuid.uuid5(uuid.UUID(t['task_id']),'operator-maintenance-boundary:1'))
audit={'reason':'Worker interrupted by operator Keva maintenance after click intent, before tap return; old send outcome remains unconfirmed; no native request after restart/sync; one explicitly authorized recovery attempt with distinct wire, no automatic uncertain-send retry policy','old_prepared_at':t['prepared_at'],'old_request_id':None,'recovery_marker':marker}
with q.db:
 q.db.execute('insert into failed_attempts values(?,?,?,?,?,?,?,?)',(t['task_id'],0,t['wire_question'],None,None,json.dumps(audit),'operator_interrupted_send_recovery',time.time()))
 q.db.execute("update tasks set state='pending',wire_question=?,capture_retries=1,prepared_at=null,request_id=null,not_before=0,error=null where task_id=?",(t['base_wire_question']+'\n（本次采集尝试编号：'+marker+'）',t['task_id']))
 q.event(t['task_id'],'operator_interrupted_send_recovery_scheduled',json.dumps(audit))
q.db.close()
# First worker is stopped; second worker continues using already loaded code.
for file in ('unattended_core.py','unattended_worker.py','geo_batch_bridge.py'):
 dest=base/'geo-batch-code'/file
 shutil.copy2(dest,base/('before-maintenance-pause-'+file))
 shutil.copyfile(base/('maintenance-safe-'+file),dest)
subprocess.run([str(base/'worker-venv/bin/python'),'-m','unittest','test_unattended','test_geo_batch_bridge'],cwd=base/'geo-batch-code',check=True)
subprocess.run(['systemctl','start',service],check=True)
print('Interrupted attempt preserved; one controlled distinct recovery started; future maintenance pause drains current task',flush=True)

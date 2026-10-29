"""Reconcile the already finished ordinal 15 answer; never send it again."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,sqlite3,subprocess,time,os
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue,lookup
from unattended_worker import databases
os.umask(0o077)
service='redroid-geo-products-account2.service'
assert subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
root=Path('/home/user/redroid-doubao/batches/geo-products-21x5-account2-relogin-20261013')
q=Queue(root/'tasks.sqlite')
t=dict(q.db.execute('select * from tasks where ordinal=15').fetchone())
assert t['state']=='needs_attention' and t['request_id']=='c103a658-c8df-49fc-9dda-0a20677c3186'
assert t['error']=='Send/answer is unresolved; no automatic resend'
r=lookup(databases('doubao-hpe14-account2'),t)
assert r['status']=='complete' and r['finished'] and r['request_id']==t['request_id'] and r['body_markdown'].strip() and len(r['sources'])==11
backup=root/('before-late-answer-reconcile-'+str(int(time.time()))+'.sqlite')
with sqlite3.connect(backup) as dest:q.db.backup(dest)
with q.db:
    q.db.execute("update tasks set state='prepared' where task_id=? and state='needs_attention'",(t['task_id'],))
    q.event(t['task_id'],'operator_reconcile_late_complete','Complete native answer arrived after 300-second wait timeout; same server-confirmed request/answer, 11 sources; no send/retry performed; prior attention evidence retained')
    q.complete(t['task_id'],r)
print('Ordinal 15 completed from its existing native answer, no resend. Queue:',q.summary(),flush=True)
subprocess.run(['systemctl','reset-failed',service],check=True)
subprocess.run(['systemctl','start',service],check=True)

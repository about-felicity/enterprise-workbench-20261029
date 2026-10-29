"""Recover only the proven-unsent task blocked by Android notification UI."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys, subprocess, sqlite3, os
from pathlib import Path
os.umask(0o077)
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue, lookup
from unattended_worker import Android, databases
service='redroid-geo-products.service'
state=subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip()
assert state in ('inactive','failed'),state
root=Path('/home/user/redroid-doubao/batches/geo-products-21x5-20261013')
q=Queue(root/'tasks.sqlite')
identity='d4d7819f-ab12-5d4c-a0cc-a7c4a7b47aef'
task=dict(q.db.execute('select * from tasks where task_id=?',(identity,)).fetchone())
assert task['state']=='needs_attention' and task['prepared_at'] is None and task['request_id'] is None
assert not q.db.execute("select 1 from events where task_id=? and event in ('send_intent_committed','send_click_intent_committed')",(identity,)).fetchone()
assert lookup(databases('doubao-hpe14-13-test'),task)['status']=='absent'
Android('127.0.0.1:5557','/home/user/redroid-doubao/linux-tools/platform-tools/adb').ready()
backup=root/'before-notification-recovery.sqlite'
assert not backup.exists()
with sqlite3.connect(backup) as dest:
    q.db.backup(dest)
with q.db:
    q.db.execute("update tasks set state='pending',attempts=0,error=null where task_id=? and state='needs_attention'",(identity,))
    q.event(identity,'operator_resume_proven_unsent','Notification permission dialog dismissed; no send intent/click/request existed; new chat verified. Prior failure events preserved.')
print(q.summary())
subprocess.run(['systemctl','start',service],check=True)
print('First batch resumed at ordinal 91')

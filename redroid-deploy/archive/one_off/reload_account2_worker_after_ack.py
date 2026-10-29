"""Reload Python capture only after a native ack; leave the App running."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,time,subprocess,json,os
from pathlib import Path
base=Path('/home/user/redroid-doubao');sys.path.insert(0,str(base/'geo-batch-code'))
from unattended_core import Queue,lookup
from unattended_worker import databases,atomic_json
root=base/'batches/geo-products-21x5-account2-relogin-20261013';q=Queue(root/'tasks.sqlite')
service='redroid-geo-products-account2.service';c='doubao-hpe14-account2'
end=time.monotonic()+45
while time.monotonic()<end:
 t=q.next_task()
 if t and t['state']=='prepared':
  r=lookup(databases(c),t)
  if r.get('native_request_confirmed'):
   with q.db:q.event(t['task_id'],'worker_reload_after_native_ack',r['request_id'])
   atomic_json(root/'maintenance_pause.json',{'reason':'Reload Python worker after confirmed native request; App stays running','time':time.time()})
   subprocess.run(['systemctl','stop',service],check=True)
   nxt=q.next_task()
   if nxt and nxt['state']=='prepared':
    observed=lookup(databases(c),nxt)
    assert observed.get('native_request_confirmed') or q.may_finish_unsent(nxt['task_id'])
   (root/'maintenance_pause.json').unlink()
   subprocess.run(['systemctl','start',service],check=True)
   print('Account2 Python worker reloaded at confirmed native boundary; App/request preserved',flush=True)
   raise SystemExit(0)
 time.sleep(1)
raise SystemExit('No safe native boundary observed; no service/App stopped')

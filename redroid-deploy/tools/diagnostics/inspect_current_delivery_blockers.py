"""Read current blocked capture responses only; no credentials or other chats."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue,lookup
from unattended_worker import databases
for container,batch in [('doubao-hpe14-13-test','geo-products-21x5-account1-20261014'),('doubao-hpe14-account2','geo-products-21x5-account2-relogin-20261013')]:
 root=Path('/home/user/redroid-doubao/batches')/batch
 q=Queue(root/'tasks.sqlite')
 for row in q.db.execute("select * from tasks where state='needs_attention'"):
  task=dict(row)
  result=lookup(databases(container),task)
  health=json.loads((root/'bridge_health.json').read_text())
  print(json.dumps({'container':container,'ordinal':task['ordinal'],'question':task['question'],'error':task['error'],'native_status':result.get('status'),'response_text':result.get('body_markdown'),'source_count':len(result.get('sources',[])),'delivery_errors':health.get('delivery_errors'),'captured':health.get('captured'),'geo_processed':health.get('geo_processed')},ensure_ascii=False))

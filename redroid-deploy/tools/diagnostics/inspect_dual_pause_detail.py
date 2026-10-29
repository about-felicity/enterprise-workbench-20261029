"""Inspect only current blocked tasks, their events, and visible UI controls."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,os,json,sqlite3,xml.etree.ElementTree as ET
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import Android,databases
from unattended_core import Queue
for container,serial,batch in [('doubao-hpe14-13-test','127.0.0.1:5557','geo-products-21x5-account1-20261014'),('doubao-hpe14-account2','127.0.0.1:5558','geo-products-21x5-account2-relogin-20261013')]:
 root=Path('/home/user/redroid-doubao/batches')/batch
 q=Queue(root/'tasks.sqlite')
 t=dict(q.db.execute("select * from tasks where state='needs_attention'").fetchone())
 print('TASK',container,{k:t[k] for k in ('task_id','ordinal','error','request_id')})
 print('EVENTS',[dict(r) for r in q.db.execute('select event,detail,time from events where task_id=? order by id',(t['task_id'],))])
 for p in databases(container):
  db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
  rows=list(db.execute('select local_message_id,message_id,server_index,status,conversation_id,fts_content from im_message where instr(content,?)>0 or instr(fts_content,?)>0',(t['task_id'],t['task_id'])))
  print('NATIVE',len(rows),[{k:r[k] for k in r.keys() if k!='fts_content'} for r in rows])
 a=Android(serial,'/home/user/redroid-doubao/linux-tools/platform-tools/adb')
 tree=ET.fromstring(a.device.dump_hierarchy())
 print('UI',json.dumps([{'id':n.get('resource-id'),'text':n.get('text'),'desc':n.get('content-desc'),'clickable':n.get('clickable'),'bounds':n.get('bounds')} for n in tree.iter('node') if n.get('text') or n.get('content-desc') or n.get('clickable')=='true'],ensure_ascii=False))

import sqlite3,json,sys
from pathlib import Path
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261027-090005-e7c7269a')
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 t=dict(db.execute('select * from tasks where ordinal=18').fetchone())
 print(json.dumps({'task':t},ensure_ascii=False))
 events=[dict(r) for r in db.execute('select * from events where task_id=? order by time',(t['task_id'],))]
 print(json.dumps({'events_first':events[:12],'events_last':events[-12:],'count':len(events)},ensure_ascii=False))
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao']
from android_ui import Android
a=Android();print('CURRENT',a.device.app_current());xml=a.device.dump_hierarchy()
Path('/tmp/yuanbao-stall-ui.xml').write_text(xml)
import xml.etree.ElementTree as ET
print('UI',json.dumps([n.get('text') or n.get('content-desc') for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc')],ensure_ascii=False))
from native_client import NativeClient
from unbound_history import history_index
c=NativeClient(root);c.connect()
before=json.loads((root/(t['task_id']+'.pre-send.json')).read_text())
print('NEW_HISTORY',json.dumps([r for g in history_index() for r in g if r['id'] not in before['conversations']],ensure_ascii=False))
print('NEW_MEMORY_IDS',list(set(c.script.exports_sync.conversation_ids())-set(before['conversations'])))
print('NATIVE_MATCHES',len(c.script.exports_sync.snapshot(t['wire_question'])))
c.close()

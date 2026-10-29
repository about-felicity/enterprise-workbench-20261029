"""Read only current Yuanbao batch; preserve a diagnosis before recovery."""
import json, sqlite3, sys, time, hashlib
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261022-090005-705819fb')
D=Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall');D.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
out={'at':time.time(),'health':json.loads((R/'bridge_health.json').read_text())}
row=db.execute("select * from tasks where state='prepared' order by ordinal limit 1").fetchone()
if row:
 t=dict(row);t.pop('result_json',None);out['task']=t
 out['events']=[dict(x) for x in db.execute('select * from events where task_id=? order by time desc limit 12',(t['task_id'],))]
 for suffix in ('binding','native','render'):
  p=R/(t['task_id']+'.'+suffix+'.json')
  if not p.exists():continue
  raw=json.loads(p.read_text());dest=D/('before-'+suffix+'.json')
  if not dest.exists():dest.write_text(json.dumps(raw,ensure_ascii=False))
  if suffix=='native':
   out['native']={k:raw.get(k) for k in ('message','question','last','conversation')}
   c=raw.get('content',{});out['content']={k:v for k,v in c.items() if k not in ('entities','text','data')}
   out['entities']=raw.get('entities',[])
 from native_storage import databases,open_readonly
 binding=json.loads((R/(t['task_id']+'.binding.json')).read_text());cid=binding['conversation_id']
 out['store']=[]
 for p in databases():
  with open_readonly(p) as store:
   tables={}
   for table in ('ChatMessages','ChatMessagesContecnt','ChatMessageEntities','ChatConversationDetail'):
    rows=[dict(x) for x in store.execute('select * from '+table+' where conversation_id=?',(cid,))]
    tables[table]=rows
   storefile=D/'before-store.json'
   if not storefile.exists():storefile.write_text(json.dumps(tables,ensure_ascii=False))
   out['store'].append({k:[{a:b for a,b in row.items() if a not in ('raw_data','object_json','replaces_json')} for row in rows] for k,rows in tables.items()})
 from android_ui import Android
 a=Android();xml=a.device.dump_hierarchy();(D/'before-ui.xml').write_text(xml)
 import xml.etree.ElementTree as ET
 out['ui_text']=[n.get('text') or n.get('content-desc') for n in ET.fromstring(xml).iter('node') if n.get('text') or n.get('content-desc')]
 for local in ('native_client.py','native_core.py','native_models.js','history_refresh.py'):
  out.setdefault('sha',{})[local]=hashlib.sha256(Path('/home/user/redroid-yuanbao',local).read_bytes()).hexdigest()
 (D/'inspect.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False)[:23000])

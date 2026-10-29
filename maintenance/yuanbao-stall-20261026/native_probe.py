import sys,json,sqlite3,traceback,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code']
from native_client import NativeClient
from question_only_adapters import android
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261025-090004-5b28fa76')
with sqlite3.connect(R/'tasks.sqlite') as db:
 db.row_factory=sqlite3.Row;t=dict(db.execute("select * from tasks where state='prepared'").fetchone())
c=NativeClient(R);out={}
try:
 c.connect();rows=c.script.exports_sync.snapshot(t['wire_question']);out['snapshots']=rows
 for row in rows:
  h=row.get('value',{}).get('h',{})
  if not h.get('conversationId') or not h.get('msgId'):continue
  key=h['conversationId']+'/'+h['msgId']
  try:out.setdefault('known',{})[key]=c.script.exports_sync.read_known(h['conversationId'],h['msgId'])
  except Exception:out.setdefault('known_errors',{})[key]=traceback.format_exc()

except Exception:out['error']=traceback.format_exc()
finally:c.close()
d=android('yuanbao',None,None).device
out['ui']=[{k:n.get(k) for k in ('text','resource-id','content-desc','bounds') if n.get(k)} for n in ET.fromstring(d.dump_hierarchy()).iter('node') if n.get('text') or n.get('content-desc')]
Path('/opt/monitor/geo-capture/maintenance/20261026-yuanbao-stall/native-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({'snapshots':[{'kind':r['kind'],'question':r.get('value',{}).get('v'),'context':r.get('value',{}).get('h')} for r in out.get('snapshots',[])],'errors':out.get('known_errors'),'error':out.get('error'),'known':{k:{'last':v.get('last'),'message':v.get('message'),'content':v.get('content'),'question':v.get('question')} for k,v in out.get('known',{}).items()}},ensure_ascii=False))

import json,sqlite3,sys,time,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code']
from question_only_adapters import android
from native_client import NativeClient
from native_core import text_entities,enum
from history_refresh import stored_history,memory_history
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215')
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence')
with sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;t=dict(db.execute('select * from tasks where ordinal=125').fetchone())
raw=json.loads((R/(t['task_id']+'.native.json')).read_text());binding=json.loads((R/(t['task_id']+'.binding.json')).read_text())
d=android('yuanbao',None,None).device;c=NativeClient(R)
out={'at':time.time(),'native_keys':list(raw),'body':text_entities(raw.get('entities',[])),'entities':raw.get('entities'),
 'ui':[{k:n.get(k) for k in ('text','resource-id','content-desc','bounds') if n.get(k)} for n in ET.fromstring(d.dump_hierarchy()).iter('node') if n.get('text') or n.get('content-desc')]}
try:
 out['observed']=c.lookup(t);out['memory_history']=c.history_entries()[:5]
 out['stored_proof']=stored_history(binding,t,raw)
 out['memory_proof']=memory_history(binding,t,raw,out['memory_history'])
except Exception as e:out['error']=type(e).__name__+': '+str(e)[:500]
finally:c.close()
(D/'live.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False)[:18000])

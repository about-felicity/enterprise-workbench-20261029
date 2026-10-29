import sys,json,sqlite3,traceback,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code']
from native_client import NativeClient
from question_only_adapters import android
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261025-090004-5b28fa76')
with sqlite3.connect(R/'tasks.sqlite') as db:
 db.row_factory=sqlite3.Row;t=dict(db.execute("select * from tasks where state='prepared'").fetchone())
c=NativeClient(R);out={}
try:out['lookup']=c.lookup(t)
except Exception:out['error']=traceback.format_exc()
finally:c.close()
d=android('yuanbao',None,None).device
out['ui']=[{k:n.get(k) for k in ('text','resource-id','content-desc','bounds') if n.get(k)} for n in ET.fromstring(d.dump_hierarchy()).iter('node') if n.get('text') or n.get('content-desc')]
print(json.dumps(out,ensure_ascii=False))

import json,sys,sqlite3,traceback,time
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from question_only_adapters import yuanbao_reader,android
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261022-090005-705819fb')
with sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;task=dict(db.execute("select * from tasks where state='prepared' order by ordinal limit 1").fetchone())
 out={'at':time.time(),'ordinal':task['ordinal'],'question':task['question'],'events':[dict(r) for r in db.execute('select event,detail,time from events where task_id=? order by id desc limit 10',(task['task_id'],))]}
r=yuanbao_reader(root)
try:
 result=r.lookup(task);out['lookup']={k:result.get(k) for k in ('status','reason','request_id','conversation_id')}
except Exception as e:out['error']={'type':type(e).__name__,'detail':str(e)[:1800],'stack':[{'file':v.filename,'line':v.lineno,'name':v.name} for v in traceback.extract_tb(e.__traceback__)]}
finally:r.close()
from history_refresh import stored_history,memory_history
binding=json.loads((root/(task['task_id']+'.binding.json')).read_text());native=json.loads((root/(task['task_id']+'.native.json')).read_text())
out['stored_history_proof']=stored_history(binding,task,native)
try:
 entries=r.history_entries();out['memory_history_proof']=memory_history(binding,task,native,entries);out['original_titles']=[v for v in entries if v.get('conversation_id')==binding['conversation_id']]
finally:r.close()
for suffix in ('binding','native','render'):
 p=root/(task['task_id']+'.'+suffix+'.json')
 if p.exists():
  raw=json.loads(p.read_text());out[suffix]={k:raw.get(k) for k in ('conversation_id','server_answer_id','message','conversation','content') if k in raw}
device=android('yuanbao',None,None).device
out['app']=device.app_current()
import xml.etree.ElementTree as ET
out['ui']=[{k:n.get(k) for k in ('text','resource-id','content-desc') if n.get(k)} for n in ET.fromstring(device.dump_hierarchy()).iter('node') if n.get('text') or n.get('content-desc')]
(D/'yuanbao-transport.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False)[:7500])

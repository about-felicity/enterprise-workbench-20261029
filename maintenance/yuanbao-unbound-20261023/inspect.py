"""Read-only App models, source identity and current queue inspection."""
import sys,json,sqlite3,time,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code']
from native_storage import app_directory,databases,open_readonly
from question_only_adapters import android
from native_client import NativeClient
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215')
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-unbound');D.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
t=dict(db.execute("select * from tasks where state='prepared' order by ordinal limit 1").fetchone());t.pop('result_json',None)
d=android('yuanbao',None,None).device
out={'at':time.time(),'task':t,'health':json.loads((R/'bridge_health.json').read_text()),'app':d.app_current(),
 'ui':[{k:n.get(k) for k in ('text','resource-id','content-desc','bounds') if n.get(k)} for n in ET.fromstring(d.dump_hierarchy()).iter('node') if n.get('text') or n.get('content-desc')]}
r=NativeClient(R)
try:
 r.connect();out['render_matches']=r.script.exports_sync.snapshot(t['wire_question']);out['memory_history']=r.history_entries()[:6]
except Exception as e:out['native_error']=type(e).__name__+': '+str(e)[:600]
finally:r.close()
hist=[]
for path in app_directory().glob('files/dtmp/Users/*/Database/history_conversation.db'):
 with open_readonly(path) as c:hist.extend(dict(v) for v in c.execute('select id,title,last_replied_at from conversation_list where coalesce(deleted_at,0)=0 order by last_replied_at desc limit 6'))
out['stored_history']=hist;matches={h['id'] for h in hist if h['title']==t['question']};out['native_store_matches']=[]
for path in databases():
 with open_readonly(path) as c:
  for cid in matches:
   rows=[dict(v) for v in c.execute('select * from ChatMessages where conversation_id=? order by message_index',(cid,))]
   contents=[dict(v) for v in c.execute('select * from ChatMessagesContecnt where conversation_id=?',(cid,))]
   out['native_store_matches'].append({'conversation_id':cid,'messages':rows,'contents':contents})
(D/('inspect-'+str(time.time_ns())+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False)[:14000])

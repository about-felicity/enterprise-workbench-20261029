import sys,json,sqlite3,traceback,subprocess
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_adapters import DoubaoReader
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261018-090003-c0f12e95')
db=sqlite3.connect('file:'+str(root/'tasks.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
t=dict(db.execute("select * from tasks where state='prepared' limit 1").fetchone())
r=DoubaoReader(root,'doubao-hpe14-13-test')
try:
 o=r.lookup(t);print('doubao_observed='+json.dumps({k:o.get(k) for k in ('status','phase','reason','native_request_confirmed','finished','request_id','answer_id','conversation_id')},ensure_ascii=False));print('body_length',len(o.get('body_markdown','')),'sources',len(o.get('sources',[])))
except Exception:traceback.print_exc()
a,b=r.paths(t);binding=json.loads(b.read_text());print('binding='+json.dumps(binding,ensure_ascii=False))
with sqlite3.connect(binding['database']) as native:
 native.row_factory=sqlite3.Row
 for row in native.execute('select * from im_message where conversation_id=? order by local_index',(binding['conversation_id'],)):
  x=dict(row);content=x.pop('content',None)
  print('message='+json.dumps({k:x.get(k) for k in ('local_message_id','message_id','user_type','server_index','local_index','status')},ensure_ascii=False))
  if content:
   try:
    blocks=json.loads(content);print('content_summary='+json.dumps(blocks,ensure_ascii=False)[:3500])
   except Exception:print('content_type',type(content).__name__)
print('yuanbao_app_process',subprocess.run(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat'],capture_output=True,text=True).returncode)

import json,sqlite3,sys,time,traceback
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_adapters import DoubaoReader
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao2-20261020-090001-6bcafb90')
db=sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
task=dict(db.execute("select * from tasks where state in ('prepared','needs_attention') order by ordinal limit 1").fetchone())
print('task',json.dumps({k:task.get(k) for k in ('task_id','ordinal','question','state','prepared_at','request_id','answer_id','capture_retries','error')},ensure_ascii=False))
print('events',json.dumps([dict(r) for r in db.execute('select id,time,event,detail from events where task_id=? order by id desc limit 12',(task['task_id'],))],ensure_ascii=False))
reader=DoubaoReader(root,'doubao-hpe14-account2')
try:
 o=reader.lookup(task)
 print('observed',json.dumps({k:v for k,v in o.items() if k not in ('raw_answer_blocks','body_markdown','sources','citations','search_queries')},ensure_ascii=False))
 print('body_length',len(o.get('body_markdown','')),'sources',len(o.get('sources',[])))
except Exception:traceback.print_exc()
before,bound=reader.paths(task)
if bound.exists():
 binding=json.loads(bound.read_text());print('binding',json.dumps(binding,ensure_ascii=False))
 with sqlite3.connect(Path(binding['database']).as_uri()+'?mode=ro',uri=True) as native:
  native.row_factory=sqlite3.Row
  for row in native.execute('select * from im_message where conversation_id=? order by local_index',(binding['conversation_id'],)):
   row=dict(row);content=row.get('content') or ''
   print('native_message',json.dumps({k:row.get(k) for k in ('local_message_id','message_id','server_index','local_index','user_type','status')},ensure_ascii=False),'content_length',len(content),'content_prefix',str(content)[:1400])

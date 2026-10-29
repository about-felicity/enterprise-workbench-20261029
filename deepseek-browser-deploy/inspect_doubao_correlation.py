import sys,sqlite3,json
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_core import message_text,request_fingerprint
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao2-20261020-090001-6bcafb90')
taskdb=sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True);taskdb.row_factory=sqlite3.Row
t=dict(taskdb.execute("select * from tasks where state='prepared' order by ordinal limit 1").fetchone())
s=json.loads((root/(t['task_id']+'-attempt-0.pre-send.json')).read_text())
print('baseline_time',s['created_at'],'send_time',t['prepared_at'])
for item in s['databases']:
 with sqlite3.connect(Path(item['database']).as_uri()+'?mode=ro',uri=True) as d:
  d.row_factory=sqlite3.Row
  print('columns',[r[1] for r in d.execute('pragma table_info(im_message)')])
  for r in d.execute('select rowid,* from im_message where rowid>? and user_type=1 order by rowid',(item['max_rowid'],)):
   if message_text(r)!=t['question']:continue
   print('candidate',json.dumps({k:r[k] for k in r.keys() if k not in ('content','fts_content','ext')},ensure_ascii=False))
   print('prior_cid',r['conversation_id'] in item['conversations'],'prior_exact',request_fingerprint(r) in item.get('prior_requests',[]))
   print('baseline_related',json.dumps([v for v in item.get('prior_requests',[]) if v['local_message_id']==r['local_message_id'] or v['conversation_id']==r['conversation_id']],ensure_ascii=False))

import sys,json,sqlite3,time
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_adapters import DoubaoReader
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao2-20261019-090003-88e4f45b')
db=sqlite3.connect(root/'tasks.sqlite');db.row_factory=sqlite3.Row
t=dict(db.execute("select * from tasks where state='prepared'").fetchone())
print(json.dumps({'task':{k:t.get(k) for k in ['task_id','ordinal','question','prepared_at','state','send_clicks','capture_retries']}},ensure_ascii=False))
print('events',json.dumps([dict(r) for r in db.execute('select * from events where task_id=? order by time desc limit 8',(t['task_id'],))],ensure_ascii=False))
r=DoubaoReader(root,'doubao-hpe14-account2').lookup(t)
print('read',json.dumps({k:r.get(k) for k in ['status','reason','phase','native_request_confirmed','finished','body_capture_complete','source_capture_complete','native_answer_status']},ensure_ascii=False))

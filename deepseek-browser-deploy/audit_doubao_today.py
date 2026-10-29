import json,sqlite3,sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
z=ZoneInfo('Asia/Shanghai')
for name in ['geo-panel-doubao1-20261019-090810-41d5da92','geo-panel-doubao2-20261019-090003-88e4f45b']:
 r=Path('/home/user/redroid-doubao/batches')/name
 db=sqlite3.connect(r/'tasks.sqlite');db.row_factory=sqlite3.Row
 rows=db.execute("select * from tasks where state='completed'").fetchall()
 times=db.execute("select min(time),max(time) from events where event='send_click_intent_committed'").fetchone()
 groups=[dict(x) for x in db.execute("select question,count(*) n from tasks where state='completed' group by question")]
 print(json.dumps({'batch':name,'completed':len(rows),'question_counts':groups,'click_start':datetime.fromtimestamp(times[0],z).isoformat(),'click_end':datetime.fromtimestamp(times[1],z).isoformat()},ensure_ascii=False))
 if rows:
  d=json.loads(rows[0]['result_json']);print('result_keys',list(d));print('request_confirmation',json.dumps({k:v for k,v in d.items() if k in ['first_user_turn','prompt_protocol','native_request_confirmed','finished','request_created_at','created_at','native_request_time','native_answer_status']},ensure_ascii=False))
  bind=json.loads((r/(rows[0]['task_id']+'-attempt-0.binding.json')).read_text())
  with sqlite3.connect(Path(bind['database']).as_uri()+'?mode=ro',uri=True) as native:
   native.row_factory=sqlite3.Row
   x=native.execute('select * from im_message where local_message_id=?',(bind['request_id'],)).fetchone()
   print('native_time',json.dumps({k:x[k] for k in x.keys() if any(w in k for w in ['time','status'])},ensure_ascii=False))

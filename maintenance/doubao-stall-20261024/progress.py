import json,sqlite3,time
from pathlib import Path
R=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261024-090002-8e65185c');D=Path('/opt/monitor/geo-capture/maintenance/20261024-doubao-stall')
with sqlite3.connect('file:'+str(R/'tasks.sqlite')+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;task=dict(db.execute('select * from tasks where ordinal=53').fetchone());result=json.loads(task.pop('result_json') or '{}')
 events=[dict(r) for r in db.execute('select event,detail,time from events where task_id=? order by time',(task['task_id'],))]
 counts=dict(db.execute('select state,count(*) from tasks group by state'))
 next_task=db.execute("select ordinal,state,request_id from tasks where state!='completed' order by ordinal limit 1").fetchone()
out={'at':time.time(),'health':json.loads((R/'bridge_health.json').read_text()),'counts':counts,'task53':task,'evidence':{k:result.get(k) for k in ['request_id','answer_id','conversation_id','first_user_turn','native_request_confirmed']},'body_length':len(result.get('body_markdown','')),'sources':len(result.get('sources',[])),'events53':events,'next':dict(next_task) if next_task else None}
(D/'progress.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))

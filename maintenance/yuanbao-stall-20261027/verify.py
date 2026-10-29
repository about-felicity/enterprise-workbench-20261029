import json,sqlite3,time
from pathlib import Path
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261027-090005-e7c7269a')
with sqlite3.connect(R/'tasks.sqlite') as db:
 db.row_factory=sqlite3.Row
 tasks=[dict(r) for r in db.execute('select ordinal,task_id,state,request_id,answer_id,capture_retries,error from tasks where ordinal between 18 and 21')]
 for t in tasks:t['events']=[dict(r) for r in db.execute('select event,detail,time from events where task_id=? order by time desc limit 5',(t['task_id'],))]
result={'time':time.time(),'health':json.loads((R/'bridge_health.json').read_text()),'tasks':tasks}
Path('/tmp/yuanbao27-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))

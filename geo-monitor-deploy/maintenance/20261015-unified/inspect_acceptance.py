import json,sqlite3,time
from pathlib import Path
p=json.loads(Path('/opt/monitor/geo-capture/question_only_acceptance_current.json').read_text())
for model,job in p['jobs'].items():
 base=Path('/home/user/redroid-yuanbao' if model=='yuanbao' else '/home/user/redroid-doubao');root=base/'batches'/job['batch']
 h=json.loads((root/'bridge_health.json').read_text());db=sqlite3.connect(root/'tasks.sqlite');db.row_factory=sqlite3.Row
 rows=[dict(r) for r in db.execute("select task_id,state,prepared_at,error,request_id from tasks order by ordinal")]
 events=[dict(r) for r in db.execute("select event,detail from events where event!='enqueued' order by time desc limit 8")]
 print(json.dumps({'model':model,'health':{k:h.get(k) for k in ('captured','geo_processed','status')},'tasks':rows,'events':events},ensure_ascii=False));db.close()

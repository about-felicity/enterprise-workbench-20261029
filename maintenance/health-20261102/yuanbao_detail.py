import json,sqlite3
from pathlib import Path
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261102-090004-bb1beb6a')
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 t=dict(db.execute('select * from tasks where ordinal=6').fetchone());print('TASK',json.dumps(t,ensure_ascii=False))
 print('EVENTS',json.dumps([dict(x) for x in db.execute('select * from events where task_id=? order by time desc limit 12',(t['task_id'],))],ensure_ascii=False))
for p in root.glob(t['task_id']+'*'):
 if p.is_file() and p.suffix=='.json':print('FILE',p.name,p.read_text()[:22000])
print('CONFIG',(root/'config.json').read_text() if (root/'config.json').exists() else '')

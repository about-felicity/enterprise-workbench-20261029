import hashlib,json,sqlite3,subprocess
from pathlib import Path
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261102-090004-bb1beb6a')
work=Path('/home/user/redroid-yuanbao/maintenance/repair-20261102')
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 print('COUNTS',dict(db.execute('select state,count(*) from tasks group by state')))
 for r in db.execute('select ordinal,state,capture_retries,request_id,error from tasks where ordinal between 6 and 9'):print('TASK',dict(r))
 before=json.loads((work/'completed-before.json').read_text())
 now={r['task_id']:hashlib.sha256(r['result_json'].encode()).hexdigest() for r in db.execute("select task_id,result_json from tasks where state='completed'")}
 assert all(now.get(k)==v for k,v in before.items());print('PRESERVED',len(before))
print('HEALTH',(root/'bridge_health.json').read_text())
p=Path('/home/user/redroid-doubao/geo-batch-code/question_only_worker.py');print('HASH',hashlib.sha256(p.read_bytes()).hexdigest())
print(subprocess.run(['journalctl','-u','geo-native@'+root.name+'.service','-n','8','--no-pager','-o','cat'],capture_output=True,text=True).stdout)

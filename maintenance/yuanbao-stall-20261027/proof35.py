import sys,json,sqlite3
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code']
from history_refresh import original_pair_matches,stored_history,memory_history,stored_drawer_proof
from native_client import NativeClient
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261027-090005-e7c7269a')
db=sqlite3.connect(R/'tasks.sqlite');db.row_factory=sqlite3.Row;t=dict(db.execute('select * from tasks where ordinal=35').fetchone());id=t['task_id']
n=json.loads((R/(id+'.native.json')).read_text());b=json.loads((R/(id+'.binding.json')).read_text())
print('PAIR',original_pair_matches(b,t,n));print('STORED',stored_history(b,t,n))
c=NativeClient(R);print('MEMORY',memory_history(b,t,n,c.history_entries()));c.close()
print(json.dumps({k:n.get(k) for k in ['question','message','content','conversation']},ensure_ascii=False)[:7000])
for p in R.glob(id+'*history*.json'):print(p.name,p.read_text())

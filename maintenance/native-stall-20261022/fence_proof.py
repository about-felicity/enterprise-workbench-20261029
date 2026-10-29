import sys,json,sqlite3,time,hashlib
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from question_only_adapters import DoubaoReader
from runtime_reliability import CompletionFence
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');old=json.loads((D/'before.json').read_text());r=next(r for r in old['batches'] if r['model']=='doubao1');root=Path(r['root']);tid=r['task']['task_id']
with sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;task=dict(db.execute('select * from tasks where task_id=?',(tid,)).fetchone())
reader=DoubaoReader(root,'doubao-hpe14-13-test');fence=CompletionFence();a=reader.lookup(task);first=fence.ready(tid,a);time.sleep(3);b=reader.lookup(task);second=fence.ready(tid,b)
print(json.dumps({'first':first,'second':second,'first_status':a.get('status'),'second_status':b.get('status'),'different_keys':[k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)],'body_length':len(b.get('body_markdown','')),'sources':len(b.get('sources',[]))}))
(D/'fence-proof.json').write_text(json.dumps({'first':a,'second':b,'ready':second},ensure_ascii=False))

import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_adapters import DoubaoReader
from question_only_core import correlate
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261015-175827-7cb020bc')
db=sqlite3.connect(root/'tasks.sqlite');db.row_factory=sqlite3.Row;task=dict(db.execute('select * from tasks where ordinal=1').fetchone());db.close()
reader=DoubaoReader(root,'doubao-hpe14-13-test');before,bound=reader.paths(task)
print(json.dumps({'before_name':before.name,'bound_exists':bound.exists(),'question':task['question'],'correlation':correlate(json.loads(before.read_text()),task['question'])},ensure_ascii=False))
result=reader.lookup(task)
print(json.dumps({'status':result['status'],'body_length':len(result.get('body_markdown','')),'sources':len(result.get('sources',[])),'binding':bound.exists()}))

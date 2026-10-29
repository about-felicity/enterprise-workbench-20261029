import sys,json,sqlite3,shutil,traceback
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261026-yuanbao-stall');S=D/'stage';sys.path[:0]=[str(S/'yuanbao-deploy'),str(S/'redroid-deploy'),'/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code']
from question_only_adapters import yuanbao_reader
from history_refresh import stored_history
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261025-090004-5b28fa76')
with sqlite3.connect(R/'tasks.sqlite') as db:
 db.row_factory=sqlite3.Row;t=dict(db.execute("select * from tasks where state='prepared'").fetchone())
T=D/'probe-copy';T.mkdir(exist_ok=True);shutil.copy2(R/(t['task_id']+'.pre-send.json'),T/(t['task_id']+'.pre-send.json'))
c=yuanbao_reader(T)
class ReadOnlyLedger:
 def bind(self,*args):pass
c.ledger=ReadOnlyLedger()
try:
 value=c.lookup(t);binding=json.loads((T/(t['task_id']+'.binding.json')).read_text());native=json.loads((T/(t['task_id']+'.native.json')).read_text());print(json.dumps({'result':{k:v for k,v in value.items() if k!='native_snapshot'},'binding':binding,'history_proof':stored_history(binding,t,native)},ensure_ascii=False))
except Exception:print(traceback.format_exc())
finally:c.close()


# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue,lookup
from unattended_worker import databases
q=Queue('/home/user/redroid-doubao/batches/geo-products-21x5-account2-relogin-20261013/tasks.sqlite')
task=q.next_task()
if not task: raise SystemExit('No pending task')
print(json.dumps({k:task[k] for k in ('task_id','state','ordinal','request_id','prepared_at')},ensure_ascii=False))
for path in databases('doubao-hpe14-account2'):
    c=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
    c.row_factory=sqlite3.Row
    for row in c.execute('select local_message_id,conversation_id,message_id,server_index,status,message_status,sender_id from im_message where instr(content,?)>0 or instr(fts_content,?)>0',(task['task_id'],task['task_id'])):
        result=dict(row); result['sender_id']='***'+str(result['sender_id'])[-6:]
        print(json.dumps(result))
try:
    r=lookup(databases('doubao-hpe14-account2'),task)
    print(json.dumps({k:v for k,v in r.items() if k in ('status','finished','request_id','answer_id')},ensure_ascii=False))
except Exception as exc: print(type(exc).__name__,str(exc))


# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue,lookup,parse_blocks
from unattended_worker import databases
q=Queue('/home/user/redroid-doubao/batches/geo-products-21x5-account2-relogin-20261013/tasks.sqlite')
for row in q.db.execute("select * from tasks where state='needs_attention'"):
 t=dict(row);print({k:t[k] for k in ('task_id','ordinal','question','prepared_at','request_id','error')})
 print('lookup',{k:v for k,v in lookup(databases('doubao-hpe14-account2'),t).items() if k in ('status','request_id','answer_id','finished')})
 for p in databases('doubao-hpe14-account2'):
  db=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
  rows=list(db.execute('select * from im_message where instr(content,?)>0',(t['task_id'],)))
  for r in rows:
   print('request',{k:r[k] for k in ('local_message_id','conversation_id','message_id','server_index','status','local_index')})
   for a in db.execute('select * from im_message where conversation_id=? and user_type=2 and local_index>? order by local_index',(r['conversation_id'],r['local_index'])):
    blocks=parse_blocks(a['content'])
    print('answer',{'local_id':a['local_message_id'],'status':a['status'],'message_id':a['message_id'],'server_index':a['server_index'],'blocks':[{'finished':b.get('is_finish'),'types':list(b['content']),'text_length':len(b['content'].get('text_block',{}).get('text','')),'sources':len(b['content'].get('search_query_result_block',{}).get('results',[]))} for b in blocks]})

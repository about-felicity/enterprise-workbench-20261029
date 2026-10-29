
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,sqlite3,time
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue,lookup,parse_blocks
from unattended_worker import databases
for c,b in [('doubao-hpe14-13-test','geo-products-21x5-account1-20261014'),('doubao-hpe14-account2','geo-products-21x5-account2-relogin-20261013')]:
 q=Queue(Path('/home/user/redroid-doubao/batches')/b/'tasks.sqlite')
 t=q.next_task()
 if not t:continue
 print(c,{k:t[k] for k in ('ordinal','state','request_id','prepared_at')},'age',time.time()-(t['prepared_at'] or time.time()))
 r=lookup(databases(c),t);print('lookup',{k:v for k,v in r.items() if k in ('status','request_id','answer_id','native_request_confirmed')})
 if r.get('request_id'):
  for p in databases(c):
   d=sqlite3.connect(p.as_uri()+'?mode=ro',uri=True);d.row_factory=sqlite3.Row
   req=d.execute('select * from im_message where local_message_id=?',(r['request_id'],)).fetchone()
   if not req:continue
   print('native_request',{k:req[k] for k in ('message_id','server_index','status','conversation_id')})
   for a in d.execute('select * from im_message where conversation_id=? and user_type=2 and local_index>?',(req['conversation_id'],req['local_index'])):
    print('native_answer',a['local_message_id'],[{'finished':x.get('is_finish'),'types':list(x['content']),'text_length':len(x['content'].get('text_block',{}).get('text',''))} for x in parse_blocks(a['content'])])

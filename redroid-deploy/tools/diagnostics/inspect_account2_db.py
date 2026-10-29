
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,sqlite3
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import databases
for p in databases('doubao-hpe14-account2'):
    c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
    c.row_factory=sqlite3.Row
    print('database',p.name,'roles',c.execute('select user_type,count(*) from im_message group by user_type').fetchall())
    print('columns',[r[1] for r in c.execute('pragma table_info(im_message)')])
    for r in c.execute('select local_message_id,conversation_id,local_index,user_type,status,message_status,message_id,server_index,fts_content,content from im_message order by rowid desc limit 4'):
        v=dict(r)
        v['content']=str(v['content'])[:1600]
        print(json.dumps(v,ensure_ascii=False))

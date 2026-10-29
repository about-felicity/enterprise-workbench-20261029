
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,sqlite3
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import databases
from active_database_accounts import current_uid
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    uid=current_uid(name)
    path=next(p for p in databases(name) if p.name=='im_database_'+uid)
    c=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True);c.row_factory=sqlite3.Row
    tables=[r[0] for r in c.execute("select name from sqlite_master where type='table'")]
    print(name,'tables',tables)
    for table in tables:
        if table=='im_conversation':
            print('table',table,'columns',[r[1] for r in c.execute('pragma table_info('+table+')')],'count',c.execute('select count(*) from '+table).fetchone()[0])
            columns=[r[1] for r in c.execute('pragma table_info('+table+')')]
            wanted=[k for k in columns if k in ('conversation_id','local_conversation_id','status','conversation_type','type','version','is_deleted','is_dissolved','bot_id','short_id')]
            if wanted:print([dict(r) for r in c.execute('select '+','.join(wanted)+' from '+table+' order by rowid desc limit 4')])


# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json
from pathlib import Path
import sqlite3
import subprocess
container = json.loads(subprocess.check_output(['docker','inspect','doubao-redroid-redroid-1']))[0]
mount = next(m['Source'] for m in container['Mounts'] if m['Destination']=='/data')
for path in (Path(mount)/'data/com.larus.nova/databases').glob('im_database_*'):
    if path.name.endswith(('-wal','-shm','-journal')):
        continue
    try:
        with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
            rows=db.execute("select user_type,content_type,status,message_status,count(*) from im_message group by user_type,content_type,status,message_status").fetchall()
            print('role/type/state counts:',rows)
            for row in db.execute("select user_type,content_type,status,message_status,local_index from im_message where fts_content like '%官方地址%' order by create_time"):
                print('Test request/answer roles:',row)
            for row in db.execute("select content from im_message where user_type=2 and (fts_content like '%官方地址%' or fts_content like '%预约%' or fts_content like '%元组%')"):
                try:
                    print('Answer block schemas:',[(b.get('block_type'),list(b.get('content',{})),b.get('is_finish')) for b in json.loads(row[0])])
                    print('PC event metadata:',[b.get('content',{}).get('pc_event_block') for b in json.loads(row[0])])
                except (ValueError,TypeError):
                    print('Legacy non-block message')
    except sqlite3.DatabaseError:
        print('Skipped incompatible IM store')

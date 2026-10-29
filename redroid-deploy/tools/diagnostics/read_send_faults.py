
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sqlite3,json
p='/home/user/redroid-doubao/hpe14-acceptance/tasks.sqlite';db=sqlite3.connect(p);db.row_factory=sqlite3.Row
for r in db.execute("select task_id,event,detail,time from events where event='send_uncertain'"):
 print(json.dumps(dict(r)))

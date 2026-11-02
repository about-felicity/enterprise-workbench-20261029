import sqlite3,json
from datetime import datetime
from zoneinfo import ZoneInfo
print('TIME',datetime.now(ZoneInfo('Asia/Shanghai')).isoformat())
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 for table in ['costs','studio_cost_scopes']:
  print('SCHEMA',table,json.dumps(db.execute('pragma table_info('+table+')').fetchall()))

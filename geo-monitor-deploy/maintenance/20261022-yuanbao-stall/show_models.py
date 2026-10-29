import json
from pathlib import Path
rows=json.loads(Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall/classes.json').read_text())
for row in rows:
 if row['name'].endswith(('.Conversation','.ConversationInfo','.ConversationNetworkLoadingVM','.UIConversationBaseContext')):
  print(json.dumps(row,ensure_ascii=False))
import sqlite3
db=sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
r=dict(db.execute("select * from daily_tasks where model='yuanbao' and day='2026-10-22'").fetchone())
print('daily',json.dumps(r,ensure_ascii=False))

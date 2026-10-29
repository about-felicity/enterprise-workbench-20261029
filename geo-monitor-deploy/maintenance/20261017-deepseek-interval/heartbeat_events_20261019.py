import sqlite3,json
from pathlib import Path
for name,root in [('doubao1','/home/user/redroid-doubao/batches/geo-panel-doubao1-20261018-090003-c0f12e95'),('yuanbao','/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261018-090005-1655ce1c')]:
 db=sqlite3.connect('file:'+root+'/tasks.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
 print(name)
 for r in db.execute('select * from events order by rowid desc limit 4'):print(json.dumps(dict(r),ensure_ascii=False)[:2200])

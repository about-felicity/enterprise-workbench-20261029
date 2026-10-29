import sys,json
sys.path.insert(0,'/home/user/redroid-yuanbao')
from native_storage import databases,open_readonly
for p in databases():
 with open_readonly(p) as db:
  tables=[r[0] for r in db.execute("select name from sqlite_master where type='table'")]
  for table in tables:
   cols=[r[1] for r in db.execute('pragma table_info("'+table+'")')]
   if any('title' in c.lower() or 'cid' in c.lower() for c in cols):
    print(table,cols)
    for col in cols:
     if 'cid' in col.lower() or 'conversation' in col.lower():
      rows=[dict(r) for r in db.execute('select * from "'+table+'" where "'+col+'"=?',('0RRIw2HvYau',))]
      if rows:print('MATCH',json.dumps(rows,ensure_ascii=False)[:3500])

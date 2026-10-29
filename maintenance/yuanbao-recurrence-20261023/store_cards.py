import json,sys
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-yuanbao')
from native_storage import databases,open_readonly
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence');cid='0RTB4lSYXbs';out=[]
for path in databases():
 with open_readonly(path) as db:
  for row in db.execute("select name from sqlite_master where type='table'"):
   table=row[0];cols=[r[1] for r in db.execute('pragma table_info("'+table+'")')]
   if 'conversation_id' not in cols:continue
   rows=[dict(r) for r in db.execute('select * from "'+table+'" where conversation_id=?',(cid,))]
   if rows:out.append({'table':table,'columns':cols,'rows':rows})
(D/'store-cards.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for row in out:
 print(json.dumps({'table':row['table'],'columns':row['columns'],'rows':len(row['rows']),'sample':str(row['rows'][0])[:950]},ensure_ascii=False))

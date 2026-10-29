import json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import databases
from question_only_core import message_text
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261015-175827-7cb020bc')
file=next(root.glob('*.pre-send.json'));before=json.loads(file.read_text())
summary=[]
for item in before['databases']:
 with sqlite3.connect(Path(item['database']).as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  rows=db.execute('select rowid,* from im_message where rowid>? order by rowid',(item['max_rowid'],)).fetchall()
  requests=[]
  for row in rows:
   if row['user_type']==1:requests.append({'rowid':row['rowid'],'native_text':message_text(row),'cid':row['conversation_id'],'prior_cid':row['conversation_id'] in item['conversations']})
  latest=[{'rowid':r['rowid'],'fts':r['fts_content'],'type':r['user_type']} for r in db.execute('select rowid,* from im_message order by rowid desc limit 4')]
  summary.append({'baseline_max':item['max_rowid'],'current_max':db.execute('select max(rowid) from im_message').fetchone()[0],'new_rows':len(rows),'requests':requests,'latest':latest})
print(json.dumps({'databases_at_baseline':len(before['databases']),'current_databases':len(databases('doubao-hpe14-13-test')),'rows':summary},ensure_ascii=False))

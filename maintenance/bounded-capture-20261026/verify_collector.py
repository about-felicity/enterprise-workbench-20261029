import tempfile,os
from pathlib import Path
from creation.search_capture import BoundedRecovery,bounded_automatic
from geo_source_cards.journal import Journal
os.environ['GEO_UNATTENDED']='1'
for model in ['baidu_ai','wenxin_card']:
 with tempfile.TemporaryDirectory() as tmp:
  r=Path(tmp);j=Journal(r/'tasks.sqlite');task=dict(j.plan('fixture',model,['fixture question'],1,r/'results.jsonl')[0]);recovery=BoundedRecovery(j,r)
  for n in range(3):
   with j.db:j.db.execute("update captures set state='capturing'")
   result=recovery.failure(task,RuntimeError('Required source links are missing'))
   assert result['exhausted']==(n==2)
  bounded_automatic(j,'fixture');assert j.db.execute('select state from captures').fetchone()[0]=='failed_deferred';j.close()
print('actual collector runtime: both channels bounded; restart retains missing state')

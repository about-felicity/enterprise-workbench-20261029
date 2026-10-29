"""Read-only current trial gates and exact remaining original article budgets."""
import sys,json,time,sqlite3
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.staged_editorial import check,research_for_writer
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended');rows=[]
for identity in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e'):
 root=runtime.job_root(identity)
 assert runtime.read(root/'control.json').get('paused')
 for writer in sorted((root/'days/2026-10-21/jobs').glob('*/*/writer')):
  row={'job':identity,'category':writer.parent.parent.name,'number':int(writer.parent.name)}
  try:row['failures']=check(research_for_writer(writer),writer)['failures']
  except Exception as e:row['error']=str(e)
  with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
   row['charged']=db.execute("select coalesce(sum(c.charged),0) from costs c join studio_cost_scopes s on c.id=s.id where s.job=? and (c.category='' or (c.category=? and (c.article='shared' or c.article=?)))",(identity,row['category'],str(row['number']))).fetchone()[0]
  rows.append(row)
out={'at':time.time(),'articles':rows};(D/'current-gates.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))

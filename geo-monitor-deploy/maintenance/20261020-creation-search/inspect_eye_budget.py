import json,sqlite3,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1792479954-8a96bc88');job=runtime.read(root/'job.json');active=runtime.read(root/'api/active.json')
t=runtime.read(root/'queue'/active['ticket']/'ticket.json');run=root/'api/runs'/active['run_id']
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 costs=db.execute('select c.category,c.article,c.stage,count(*),sum(c.charged) from costs c join studio_cost_scopes s on s.id=c.id where s.job=? group by c.category,c.article,c.stage',(job['job_id'],)).fetchall()
print(json.dumps({'costs':costs,'active':active,'ticket':t,'call_files':[p.name for p in (run/'call').glob('*')],'budget_limits':job['budget_limits']},ensure_ascii=False))
for p in sorted((root/'days'/job['date']/'jobs').glob('*/01/review/result.json')):
 r=runtime.read(p);print(json.dumps({'file':str(p),'failures':r.get('failures'),'checks':r.get('checks'),'explanation':r.get('explanation')},ensure_ascii=False))

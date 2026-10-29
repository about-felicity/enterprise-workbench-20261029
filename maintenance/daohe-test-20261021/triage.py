import sys,json,sqlite3
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');s=runtime.read(M/'task.json');t=runtime.read(studio.day_path(s['plan_id'],s['date']));rows=[]
for jid in t['jobs'].values():
 root=runtime.job_root(jid)
 tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 rows.append({'job':jid,'active':runtime.read(root/'api/active.json'),'failures':[{'id':v['id'],'stage':v['stage'],'meta':v['meta'],'state':v['state'],'error':v.get('error')} for v in tickets if v.get('error')], 'materialization_errors':[{'run':p.parent.name,**runtime.read(p)} for p in (root/'api/runs').glob('*/materialization_error.json')]})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 fees=db.execute('select s.job,c.category,c.article,c.stage,count(*),sum(c.charged),sum(case when c.charged is null then c.reserved else 0 end) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=? group by s.job,c.category,c.article,c.stage',(s['plan_id'],)).fetchall()
result={'jobs':rows,'fees':fees};(M/'triage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))

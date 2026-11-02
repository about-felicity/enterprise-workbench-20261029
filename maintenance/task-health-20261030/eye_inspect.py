import json,sys,sqlite3,urllib.request
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
pid='plan-7ec5b8a566c34569b4da63f14eed2741';day='2026-10-30'
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=25) as r:p=json.load(r)
for t in p['studio']['daily_tasks']:
 if t.get('plan_id')==pid and t.get('date')==day:print('TASK',json.dumps({k:t.get(k) for k in ['name','status','articles','writing_jobs','writing_complete','error','api_recovery']},ensure_ascii=False))
for f in (runtime.BASE/'runs').glob('*/job.json'):
 j=runtime.read(f)
 if j.get('studio_plan_id')!=pid or j.get('date')!=day:continue
 root=f.parent;failure=recovery.http_failure(root)
 print('JOB',json.dumps({'id':root.name,'question':j.get('question'),'failure':failure,'budget':j.get('budget_limits'),'control':runtime.read(root/'control.json')},ensure_ascii=False))
 if failure:
  for call in failure['calls']:print('FAILED_CALL',json.dumps(runtime.read(root/call['path']),ensure_ascii=False))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 print('COST',db.execute('select sum(coalesce(c.charged,0)),sum(case when c.charged is null then c.reserved else 0 end),sum(coalesce(c.charged,c.reserved)) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and s.task_day=?',(pid,day)).fetchone())

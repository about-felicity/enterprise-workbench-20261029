import datetime,json,time,urllib.request,sqlite3
from pathlib import Path
from zoneinfo import ZoneInfo
base=Path('/opt/monitor/geo-content')
def read(p):
 try:return json.loads(p.read_text())
 except FileNotFoundError:return {}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=35) as r:data=json.load(r)
print('HEALTH',json.dumps({'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'studio':data['studio'].get('health'),'worker':data.get('worker')},ensure_ascii=False))
for task in data['studio']['daily_tasks']:
 if task['date']=='2026-10-31' or task.get('api_recovery') or task.get('supplement'):
  print('TASK',json.dumps({k:task.get(k) for k in ['name','date','status','articles','writing_jobs','writing_complete','error','supplement','api_recovery']},ensure_ascii=False))
for p in (base/'studio/days').glob('*/*.supplement-state'):
 state=read(p)
 if state.get('status')=='needs_materials':print('LIMITED',str(p),json.dumps(state,ensure_ascii=False))
for path in (base/'runtime/runs').glob('*/job.json'):
 job=read(path);active=read(path.parent/'api/active.json')
 if job.get('studio_plan_id')=='plan-8b2b4caaed3447618ad1eab83130e5f7' and job.get('date')=='2026-10-30' and read(path.parent/'control.json').get('paused'):
  print('OLD_HTTP',json.dumps({'job':job,'active':active,'control':read(path.parent/'control.json')},ensure_ascii=False))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 for pid,day in [('plan-8b2b4caaed3447618ad1eab83130e5f7','2026-10-30')]:
  total=db.execute('select sum(coalesce(c.charged,0)),sum(case when c.charged is null then c.reserved else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and s.task_day=?',(pid,day)).fetchone()
  print('COST',pid,day,total)

import collections,datetime,hashlib,json,sqlite3,time,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
base=Path('/opt/monitor/geo-content')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
start=time.monotonic()
with op.open('http://127.0.0.1:8804/api/status',timeout=35) as r:data=json.load(r)
tasks=[t for t in data['studio']['daily_tasks'] if t['date']=='2026-10-31']
print('FINAL',json.dumps({'at':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'status_seconds':round(time.monotonic()-start,3),'health':data['studio']['health'],'articles':sum(t['articles'] for t in tasks),'counts':dict(collections.Counter(t['status'] for t in tasks)),'tasks':[{k:t.get(k) for k in ['name','status','articles','writing_complete','writing_jobs','error']} for t in tasks]},ensure_ascii=False),flush=True)
for p in (base/'runtime/runs').glob('*/job.json'):
 job=json.loads(p.read_text());root=p.parent
 if job.get('date')!='2026-10-31' or job.get('studio_plan_id') not in ['plan-c9017fa6d4684997a3370eaf9fc5a553','plan-47fbabcdee8c4807a4f895016f830dbc']:continue
 active=root/'api/active.json'
 if active.is_file():
  value=json.loads(active.read_text())
  if value.get('state')!='SUBMITTED':print('EXECUTION',root.name,json.dumps({k:value.get(k) for k in ['state','stage','run_id']},ensure_ascii=False))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 for p in data['studio']['plans']:
  if p['plan_id'] not in {t['plan_id'] for t in tasks}:continue
  charged,reserved=db.execute('select coalesce(sum(coalesce(c.charged,0)),0),coalesce(sum(case when c.charged is null then c.reserved else 0 end),0) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and s.task_day=?',(p['plan_id'],'2026-10-31')).fetchone()
  if charged or reserved:print('BUDGET',json.dumps({'plan':p.get('name'),'charged':round(charged,6),'reserved':round(reserved,6),'limit':p.get('task_budget_cny')},ensure_ascii=False))
for relative in ['creation/materials.py','creation/studio.py','creation/supplement.py','creation/client.py','creation/runtime.py','creation/source_cache.py','engine/geo_source_cards/source_analysis.py','engine/geo_source_cards/source_scope.py']:
 print('HASH',relative,hashlib.sha256((base/relative).read_bytes()).hexdigest())

import json,sys,hashlib,sqlite3,urllib.request
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
pid='plan-7ec5b8a566c34569b4da63f14eed2741';base=Path('/opt/monitor/geo-content/maintenance/eye-http-recovery-20261030');root=runtime.job_root('creation-1793344766-1768de1c')
original=runtime.read(base/'approved-before.json');assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in original.items())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=25) as r:p=json.load(r)
t=next(t for t in p['studio']['daily_tasks'] if t.get('plan_id')==pid and t.get('date')=='2026-10-30')
result={k:t.get(k) for k in ['name','status','articles','writing_jobs','writing_complete','error','api_recovery']}
a=runtime.read(root/'api/active.json');result['active']={k:a.get(k) for k in ['state','stage','run_id']};result['control']=runtime.read(root/'control.json');result['original_files_unchanged']=True
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 result['cost']=db.execute('select sum(coalesce(c.charged,0)),sum(case when c.charged is null then c.reserved else 0 end),sum(coalesce(c.charged,c.reserved)) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and s.task_day=?',(pid,'2026-10-30')).fetchone()
print(json.dumps(result,ensure_ascii=False));runtime.atomic_json(base/'latest-progress.json',result)

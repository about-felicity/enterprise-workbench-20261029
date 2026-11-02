import json,sys,hashlib,time,sqlite3
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
root=runtime.job_root('creation-1793344766-1768de1c');job=runtime.read(root/'job.json');base=Path('/opt/monitor/geo-content/maintenance/eye-http-recovery-20261030')
assert job['date']=='2026-10-30' and job['studio_plan_id']=='plan-7ec5b8a566c34569b4da63f14eed2741'
assert job['budget_limits']['task_budget_cny']==2 and job['budget_limits']['article_budget_cny']==0.35
original=runtime.read(base/'approved-before.json');assert original and all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in original.items())
failure=recovery.http_failure(root);assert failure and failure['retry_available'] and failure['run_id']=='194393a8637412d80ce677b9'
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 used=db.execute('select sum(coalesce(c.charged,c.reserved)) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and s.task_day=?',(job['studio_plan_id'],job['date'])).fetchone()[0]
 assert used<2
result=runtime.resume(root,allow_http_recovery=True)
runtime.atomic_json(base/'recovered.json',{'at':time.time(),'original_failure':failure,'result':result,'authorization':'REDACTED_CONFIGURE_LOCALLY'})
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in original.items())
print('RECOVERED',json.dumps(result,ensure_ascii=False))

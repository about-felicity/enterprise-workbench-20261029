import json,urllib.request,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation.pricing_window import resume_at
from creation.parallel import eligible
base=Path('/opt/monitor/geo-content/runtime');health=json.loads((base/'worker_health.json').read_text())
print('WORKER',json.dumps(health),flush=True)
assert resume_at(time.time()) is not None
assert not health.get('active_jobs')
assert all(not eligible(p.parent) for p in (base/'runs').glob('*/job.json'))
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8804/api/status',timeout=60) as r:data=json.load(r)
print('TODAY_STATES',json.dumps([{'name':t.get('name'),'status':t.get('status'),'error':t.get('error')} for t in data.get('studio',{}).get('daily_tasks',[]) if t.get('date')=='2026-11-02'],ensure_ascii=False),flush=True)
for service in ['geo-content-api','geo-content-worker','geo-creation-studio']:
 assert subprocess.check_output(['systemctl','is-active',service],text=True).strip()=='active'
print('VERIFIED_OFFPEAK_GATE_SERVICES_AND_API',flush=True)

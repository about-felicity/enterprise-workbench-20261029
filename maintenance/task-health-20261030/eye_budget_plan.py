import sys,json
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1793344766-1768de1c');ticket=runtime.read(root/'queue/a70578f2ee060c94d08f7c36/ticket.json');print('EXECUTION',ticket.get('execution'))
for f in sorted((root/'api/runs').rglob('output_budget_plan.json'),key=lambda f:f.stat().st_mtime,reverse=True)[:4]:print('PLAN',str(f.relative_to(root)),json.dumps(runtime.read(f)))

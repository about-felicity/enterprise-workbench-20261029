import sys,json
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1793344766-1768de1c')
for p in (root/'api/runs').glob('*/known-rejection.json'):
 if runtime.read(p).get('reason')=='article_budget_exceeded':
  print('REJECTION',p.parent.name,json.dumps(runtime.read(p)))
  for f in p.parent.rglob('output_budget_plan.json'):print('PLAN',json.dumps(runtime.read(f)))

import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
for root in (runtime.BASE/'runs').glob('creation-*'):
 j=runtime.read(root/'job.json');c=runtime.read(root/'control.json')
 if j.get('date')!='2026-10-28' or not c.get('paused'):continue
 print('JOB',root.name,j.get('question'),json.dumps(c,ensure_ascii=False))
 active=runtime.read(root/'api/active.json');print('ACTIVE',json.dumps(active));run=root/'api/runs'/active.get('run_id','none')
 for p in run.rglob('api_state.json'):
  print('CALL',str(p),json.dumps(runtime.read(p)))
  for n in ['answer.json','response.json','transport.json','transport_state.json']:
   q=p.parent/n
   if q.exists():print(n,q.stat().st_size, str(runtime.read(q))[:400])
 print('FILES',[str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()])

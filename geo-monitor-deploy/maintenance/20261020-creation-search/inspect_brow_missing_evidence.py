import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
t=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
for f in (runtime.BASE/'runs').glob('*/job.json'):
 if runtime.read(f).get('studio_plan_id')!=t['plan_id']:continue
 r=f.parent
 for p in (r/'queue').glob('*/ticket.json'):
  ticket=runtime.read(p)
  if ticket.get('state')!='needs_attention':continue
  loc=r/ticket['location'];inp=runtime.read(loc/'research_input.json');bp=inp.get('reference_design',{});run=r/'api/runs'/ticket.get('execution',{}).get('run_id','')
  answer=runtime.read(run/'call/response.json')
  print(json.dumps({'ticket':ticket['id'],'location':ticket['location'],'blueprint_products':[{'name':p['name'],'excerpt':p.get('excerpt','')[:1300]} for p in bp.get('products',[])[:2]],'run':str(run.relative_to(r)),'call_state':runtime.read(run/'call/api_state.json').get('state'),'answer':answer},ensure_ascii=False))

import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1792575159-0a8f9221')
rows=[]
for path in (root/'queue').glob('*/ticket.json'):
 j=runtime.read(path)
 if j.get('meta',{}).get('compiler_pilot_release')!='practical-v1':continue
 run=root/'api/runs'/j.get('execution',{}).get('run_id','missing')
 rows.append({'ticket':j['id'],'stage':j['stage'],'category':j['meta']['category'],'number':j['meta']['number'],
              'state':j['state'],'error':j.get('error'),'run':run.name,'materialization':runtime.read(run/'materialization_error.json'),
              'response_keys':list(runtime.read(run/'call/response.json')),'receipt':runtime.read(path.parent/'receipt.json')})
print(json.dumps(rows,ensure_ascii=False))

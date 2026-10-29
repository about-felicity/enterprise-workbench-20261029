import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1792575159-0a8f9221')
for p in sorted((root/'queue').glob('*/ticket.json')):
 j=runtime.read(p)
 if j.get('stage')!='review' or j['meta'].get('number') not in (3,4,5) or j['meta'].get('category')!='测评类':continue
 run=root/'api/runs'/j.get('execution',{}).get('run_id','missing')
 if not (run/'call/response.json').is_file() and not j['meta'].get('review_release'):continue
 print(json.dumps({'id':j['id'],'run':run.name,'created':j['created_at'],'state':j['state'],'number':j['meta']['number'],'error':j.get('error'),
 'call':runtime.read(run/'call/api_state.json').get('state'),'logic':runtime.read(run/'logic-call/api_state.json').get('state'),
 'fact':runtime.read(run/'call/response.json').get('failures'),'logic_status':runtime.read(run/'logic-call/logic_certificate.json').get('status')},ensure_ascii=False))

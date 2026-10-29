import json
from pathlib import Path
def read(p):return json.loads(p.read_text()) if p.exists() else {}
for p in Path('/opt/monitor/geo-content/runtime/runs').glob('*/job.json'):
 j=read(p);r=p.parent;c=read(r/'control.json');d=read(r/'days'/j['date']/'day.json')
 if c.get('paused') or d.get('status')=='complete':continue
 a=read(r/'api/active.json');call=read(r/'api/runs'/a.get('run_id','')/'call/api_state.json')
 print(json.dumps({'job':j['job_id'],'plan':j.get('studio_plan_id'),'name':j.get('task_name'),'date':j['date'],'preparation':j.get('preparation'),'day':d.get('status'),'planned':d.get('planned_articles'),'accepted':d.get('accepted_articles'),'active_state':a.get('state'),'stage':a.get('stage'),'call_state':call.get('state')},ensure_ascii=False))

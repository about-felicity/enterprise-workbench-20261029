import json,time,subprocess
from pathlib import Path
base=Path('/opt/monitor/geo-content')
def read(p):
 try:return json.loads(p.read_text())
 except (FileNotFoundError,ValueError):return {}
plans=[read(p) for p in (base/'studio/plans').glob('*.json')]
plans=[p for p in plans if '染发' in p.get('name','') and not p.get('deleted_at')]
for p in plans:
 print('PLAN',json.dumps({k:p.get(k) for k in ['plan_id','name','frequency','capture_time','article_target','task_budget_cny','questions']},ensure_ascii=False))
 ids={p['plan_id'] for p in plans}
for p in (base/'runtime/runs').glob('*/job.json'):
 j=read(p)
 if j.get('studio_plan_id') not in ids or j.get('date')!='2026-10-29':continue
 root=p.parent;control=read(root/'control.json');active=read(root/'api/active.json')
 print('JOB',json.dumps({'root':str(root),'question':j.get('question'),'control':control,'active':active,'day':read(root/'days/2026-10-29/day.json')},ensure_ascii=False))
 for f in root.rglob('api_state.json'):
  v=read(f)
  if v.get('state') not in ['REQUEST_UNKNOWN','HTTP_REJECTED','REQUESTING']:continue
  print('CALL',json.dumps({'path':str(f),'state':v,'age_seconds':round(time.time()-f.stat().st_mtime),'files':{n:(f.parent/n).exists() for n in ['response.json','answer.json','request.json','transport_response.json','transport_error.json']}},ensure_ascii=False))
print('API_LOG',subprocess.check_output(['journalctl','-u','geo-content-worker','--since','2026-10-29 12:00:00','-n','35','--no-pager']).decode()[-7000:])

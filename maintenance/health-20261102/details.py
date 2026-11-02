import json
from pathlib import Path
base=Path('/opt/monitor/geo-content/runtime/runs')
def read(p):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return {}
for p in base.glob('*/job.json'):
 j=read(p);root=p.parent
 if j.get('date') not in ['2026-11-01','2026-11-02']:continue
 if j.get('preparation')=='insufficient':print('MATERIAL',root.name,json.dumps(j,ensure_ascii=False))
 active=read(root/'api/active.json')
 for f in (root/'queue').glob('*/ticket.json'):
  t=read(f)
  if t.get('state') not in ['needs_attention','claimed']:continue
  print('ISSUE',root.name,j.get('question'),json.dumps(t,ensure_ascii=False),json.dumps(active,ensure_ascii=False))
  runid=t.get('execution',{}).get('run_id') or active.get('run_id')
  if not runid:continue
  run=root/'api/runs'/runid
  for a in run.rglob('*'):
   if a.is_file() and a.name in ['api_state.json','state.json','result.json','error.json']:
    print('STATE',str(a),a.read_text()[:7000])
  print('FILES',[str(x.relative_to(run)) for x in run.rglob('*') if x.is_file()])

import json,collections
from pathlib import Path
base=Path('/opt/monitor/geo-content/runtime/runs')
def read(p):
 try:return json.loads(p.read_text())
 except FileNotFoundError:return {}
for r in base.iterdir():
 j=read(r/'job.json')
 if j.get('date','')<'2026-10-26':continue
 tickets=[read(p) for p in (r/'queue').glob('*/ticket.json')];failed=[t for t in tickets if t.get('state')=='needs_attention']
 print(json.dumps({'id':r.name,'date':j['date'],'plan':j.get('studio_plan_id'),'policy':read(r/'rewrite_policy.json'),'control':read(r/'control.json'),'day':read(r/'days'/j['date']/'day.json').get('status'),'failed':[{k:t.get(k) for k in ['id','stage','error','state','location']} for t in failed],'active':read(r/'api/active.json').get('state')},ensure_ascii=False))

import json,sqlite3,time
from pathlib import Path
def read(p):
 try:return json.loads(p.read_text('utf-8-sig'))
 except FileNotFoundError:return {}
base=Path('/opt/monitor/geo-content/runtime');shared=Path('/home/user/geo-editorial/runtime-api')
items=[]
for root in [shared,*sorted((base/'runs').iterdir())]:
 if not root.is_dir():continue
 job=read(root/'job.json');control=read(root/'control.json');active=read(root/'api/active.json')
 tickets=[read(p) for p in (root/'queue').glob('*/ticket.json')]
 items.append({'root':str(root),'job_id':job.get('job_id'),'preparation':job.get('preparation'),'control':control,
  'active':active,'pending_or_claimed':sum(t.get('state') in ('pending','claimed') for t in tickets),
  'health':read(root/'geo_worker.json')})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 unknown=[dict(r) for r in db.execute('select id,state,reserved,created from costs where charged is null')]
 recent=[dict(r) for r in db.execute('select id,state,charged,created from costs where created>?',(time.time()-900,))]
procs=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
 except (FileNotFoundError,PermissionError):continue
 if 'python' in cmd and any(s in cmd for s in ('acceptance','rank01','staged','first_preflight','structure-first')):
  procs.append({'pid':p.name,'command':cmd[:500]})
print(json.dumps({'jobs':items,'unknown':unknown,'recent_costs':recent,'acceptance_processes':procs,'settings':read(shared/'settings.json')},ensure_ascii=False,indent=2))

import json,collections,time
from pathlib import Path
base=Path('/opt/monitor/geo-content/runtime')
def read(p):
 try:return json.loads(p.read_text())
 except FileNotFoundError:return {}
for row in read(base/'worker_health.json').get('active_jobs',[]):
 root=base/'runs'/row['job_id'];active=read(root/'api/active.json')
 tickets=[read(p) for p in (root/'queue').glob('*/ticket.json')]
 print(json.dumps({'job':root.name,'control':read(root/'control.json'),'active':active,'queue':dict(collections.Counter((t['stage'],t['state']).__str__() for t in tickets)),'health':read(root/'worker.json')},ensure_ascii=True))

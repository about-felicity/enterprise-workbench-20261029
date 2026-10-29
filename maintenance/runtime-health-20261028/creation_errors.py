import json,urllib.request,collections
from pathlib import Path
def read(p):
 try:return json.loads(p.read_text())
 except (ValueError,FileNotFoundError):return {}
with urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=60) as response:data=json.load(response)
tasks=data['studio']['daily_tasks'];print('SUMMARY',json.dumps({day:{'articles':sum(t['articles'] for t in tasks if t['date']==day),'states':dict(collections.Counter(t['status'] for t in tasks if t['date']==day))} for day in ['2026-10-26','2026-10-27','2026-10-28']},ensure_ascii=False))
for job in data['jobs']:
 if job.get('date','')<'2026-10-27':continue
 root=Path('/opt/monitor/geo-content/runtime/runs')/job['job_id']
 failed=[read(p) for p in (root/'queue').glob('*/ticket.json') if read(p).get('state')=='needs_attention']
 if not failed:continue
 print('JOB',json.dumps({k:job.get(k) for k in ['job_id','date','question','task_name','control','day']},ensure_ascii=False))
 for f in failed:
  print('FAILED',json.dumps({k:f.get(k) for k in ['id','stage','error','execution']},ensure_ascii=False))
  print('RECEIPT',json.dumps(read(root/'queue'/f['id']/'receipt.json'),ensure_ascii=False)[:1800])

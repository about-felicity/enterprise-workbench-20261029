import json,subprocess
from pathlib import Path
read=lambda p:json.loads(p.read_text()) if p.exists() else {}
s=read(Path('/tmp/content-health-20261029.json'));out={}
out['today_summary']=[{k:t.get(k) for k in ['name','status','articles','error']} for t in s['today_tasks']]
out['job_sample']=s['jobs'][:1]
out['attention_jobs']=[]
for t in s['today_tasks']:
 if t['status'] in ['complete','scheduled']:continue
 for q,jid in t['jobs'].items():
  root=Path('/opt/monitor/geo-content/runtime/runs')/jid
  out['attention_jobs'].append({'question':q,'id':jid,'files':{n:read(root/n) for n in ['job.json','control.json','supplement.json','days/2026-10-29/day.json']}})
out['logs']=subprocess.run(['journalctl','-u','geo-content-api','-u','geo-content-worker','-u','geo-creation-studio','--since','2026-10-28 16:00:00 UTC','-n','100','--no-pager'],capture_output=True,text=True).stdout
print(json.dumps(out,ensure_ascii=False,indent=2))

import json,hashlib,urllib.request,subprocess,os
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/task-health-20261030');base.mkdir(parents=True,exist_ok=True)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=30) as r:p=json.load(r)
summary=[{k:t.get(k) for k in ['name','plan_id','date','status','articles','writing_jobs','writing_complete','error','api_recovery']} for t in p['studio']['daily_tasks'] if t.get('date')=='2026-10-30']
(base/'status.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
print(json.dumps(summary,ensure_ascii=False))
f=Path('/opt/monitor/geo-content/creation/materials.py');print('MATERIALS_SHA',hashlib.sha256(f.read_bytes()).hexdigest())

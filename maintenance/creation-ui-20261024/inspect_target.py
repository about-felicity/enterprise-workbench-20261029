import json,urllib.request
from pathlib import Path
s=json.load(urllib.request.urlopen('http://127.0.0.1:8804/api/status'))
p=next(p for p in s['studio']['plans'] if p.get('name','').startswith('道和'))
print(json.dumps({k:v for k,v in p.items() if k in ['plan_id','article_target','questions','start_date','frequency']},ensure_ascii=False))
for j in s['jobs']:
 if j.get('studio_plan_id')==p['plan_id']:
  print(json.dumps({k:j.get(k) for k in ['job_id','date','day','control','health','queue']},ensure_ascii=False))
path=Path('/opt/monitor/geo-content/studio/days')/p['start_date']/(p['plan_id']+'.json')
t=json.loads(path.read_text());print(json.dumps({'daily_status':t.get('status'),'jobs':t.get('jobs'),'target':t['plan'].get('article_target'),'questions':len(t['plan']['questions'])},ensure_ascii=False))

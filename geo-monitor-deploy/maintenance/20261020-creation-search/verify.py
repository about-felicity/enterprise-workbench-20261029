import json,sqlite3,time,urllib.request
from pathlib import Path
root=Path('/opt/monitor/geo-content/studio/capture/plan-fbb1750d49ea45cb8d3a490b44a19e32')
plan=json.loads((root/'settings.json').read_text());health=json.loads((root/'health.json').read_text())
assert plan['search_pool']=='creation_only' and plan['channels']==['baidu_ai','wenxin_card']
assert plan['studio_plan']['task_type']=='capture_only'
assert health['search_resource_pool']=='creation_only' and health['geo_ingest_enabled'] is False
rows={}
for model in plan['channels']:
 lane=root/'days/2026-10-20'/model;dbpath=lane/'collector/tasks.sqlite'
 result={'counts':{},'results':[]}
 if dbpath.exists():
  with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
   result['counts']=dict(db.execute('select state,count(*) from captures group by state'))
 if (lane/'results.jsonl').exists():
  for line in (lane/'results.jsonl').read_text().splitlines():
   if not line.strip():continue
   row=json.loads(line);result['results'].append({k:row.get(k) for k in ('model','question','body_capture_complete','source_capture_complete','availability','task_id')})
   result['results'][-1].update(body_length=len(row.get('body','')),sources=len(row.get('sources',[])))
 rows[model]=result
with urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=30) as response:
 status=json.load(response)
item=next(v for v in status['studio']['daily_tasks'] if v['plan_id']==plan['studio_plan']['plan_id'] and v['date']=='2026-10-20')
assert item['questions']==16 and item['task_type']=='capture_only'
report={'at':time.time(),'plan_id':plan['studio_plan']['plan_id'],'health':health,'channels':rows,'panel_task':item,'no_geo_receiver':True}
Path('/tmp/creation-search-acceptance.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

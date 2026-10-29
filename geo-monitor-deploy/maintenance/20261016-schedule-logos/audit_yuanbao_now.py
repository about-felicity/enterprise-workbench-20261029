import json,sqlite3,subprocess,urllib.request
from pathlib import Path
with urllib.request.urlopen('http://127.0.0.1:3000/api/geo-capture/panel',timeout=30) as response:data=json.load(response)
m=next(m for m in data['models'] if m['id']=='yuanbao')
result={'daily':{k:m['daily'][k] for k in ('status','desired','target','completed','remaining','config')},'current':{k:m['current'][k] for k in ('batch','planned','captured','processed','state','service_state','pending_delivery')},'events':m['events'][:10]}
sql="""select coalesce(json_agg(t),'[]') from (select record->>'batch_id' batch,count(*) observations,min(r.finished_at) first_capture,max(r.finished_at) last_capture,max(e.received_at) last_received,coalesce(r.payload->>'product_review_status','unspecified') review,max(r.updated_at) last_analysis_update from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id where e.source_device='yuanbao-hpe14-android13' and r.day='2026-10-16' group by 1,6)t"""
result['database']=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True))
print(json.dumps(result,ensure_ascii=False))
Path('/opt/monitor/geo-capture/maintenance/20261016-schedule-logos/yuanbao-now.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))

"""Read-only final state evidence; no collector or model requests."""
import json,sqlite3,subprocess,time,hashlib
from pathlib import Path
B=Path('/opt/monitor/geo-capture');D=B/'maintenance/20261023-wenxin-start'
batch='geo-panel-baidu-ai-20261023-090003-1a1735de'
def read(path):return json.loads(path.read_text()) if path.exists() else None
db=sqlite3.connect(f'file:{B}/panel/control.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
rows=[dict(r) for r in db.execute("select * from daily_tasks where day='2026-10-23' and model in ('baidu_ai','wenxin_card')")]
for r in rows:r['config']=json.loads(r['config'])
sql="""select coalesce(json_agg(t),'[]') from (select e.source_device,e.record->>'batch_id' batch,count(*) n
from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id
where r.day='2026-10-23' and r.status='success' and e.source_device in ('geo-headless-baidu_ai','geo-headless-wenxin_card') group by 1,2)t"""
counts=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True,timeout=15))
live=read(D/'wenxin-live-result.json') or {};v=live.get('result',{})
result={'at':time.time(),'daily':rows,'baidu_health':read(B/'batches'/batch/'bridge_health.json'),'database_counts':counts,
'wenxin_diagnostic':{'at':live.get('at'),'diagnostic_only':live.get('diagnostic_only'),'daily_count_not_modified':live.get('daily_count_not_modified'),
'body_chars':len(v.get('body','')),'source_count':v.get('source_count'),'expected_source_count':v.get('expected_source_count'),
'body_capture_complete':v.get('body_capture_complete'),'source_capture_complete':v.get('source_capture_complete'),'question':v.get('verified_question')},
'daily_control':subprocess.check_output(['systemctl','is-active','geo-daily-control.service'],text=True).strip(),
'profile_migrations':{m:read(B/'profiles/search'/m/'migration.json') for m in ('baidu_ai','wenxin_card')},
'deployment':read(D/'deployment.json'),'regressions':read(D/'profile-test-results.json'),'recovery':read(D/'recovery-verification.json')}
(D/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False,indent=2))

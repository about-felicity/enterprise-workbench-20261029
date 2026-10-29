import json,subprocess
sql="""select json_agg(t) from (select e.source_device,e.record->>'batch_id' batch,e.record->'payload'->>'batch_id' nested_batch,count(*) n from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id where r.day='2026-10-19' and e.source_device in ('doubao-hpe14-13-test','doubao-hpe14-account2') group by 1,2,3)t"""
print(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True))

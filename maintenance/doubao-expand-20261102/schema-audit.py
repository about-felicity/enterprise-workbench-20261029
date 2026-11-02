import json,subprocess
sql="""select json_build_object('run_keys',(select json_agg(k) from jsonb_object_keys(r.payload) k),'evt_keys',(select json_agg(k) from jsonb_object_keys(e.record) k),'sources',jsonb_typeof(r.payload->'sources'),'sample_src_keys',(select json_agg(k) from jsonb_object_keys(r.payload->'sources'->0) k)) from monitor_runs r join monitor_ingest_events e using(model_id,run_id) where r.run_id='doubao-4751bae598f9ce1f0699' limit 1"""
print(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True))

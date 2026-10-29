import json,subprocess
from pathlib import Path
out=Path('/opt/monitor/geo-capture/maintenance/20261015-unified');out.mkdir(exist_ok=True)
def sql(q):return json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',q],text=True,timeout=60))
rows=sql("""select coalesce(json_agg(t),'[]') from (select r.run_id,r.sequence_no,r.day,r.question,r.serial,r.answer,array(select jsonb_object_keys(r.payload)) payload_keys,r.payload from monitor_runs r where model_id='doubao' and sequence_no in (42810,42941)) t""")
(out/'screenshot-raw-runs.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print('SCREENSHOT_RECORDS',json.dumps([{k:v for k,v in r.items() if k!='payload'} for r in rows],ensure_ascii=False))
rows=sql("""select coalesce(json_agg(t),'[]') from (select e.model_id,r.run_id,r.sequence_no,r.day,length(r.answer) normalized_length,length(coalesce(e.record->>'answerText',e.record->>'web_body','')) raw_length,r.answer=coalesce(e.record->>'answerText',e.record->>'web_body','') exact_body,e.record->>'batch_id' batch,e.record->>'capture_mode' mode,array(select jsonb_object_keys(r.payload)) payload_keys from monitor_ingest_events e join monitor_runs r on e.run_id=r.run_id and e.model_id=r.model_id where e.received_at>now()-interval '1 day' order by received_at desc limit 150) t""")
(out/'ingest-normalized-layers.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
print('NORMALIZED_DIFFS',json.dumps([r for r in rows if not r['exact_body']][:15],ensure_ascii=False))
print('TOTAL',len(rows),'EXACT',sum(r['exact_body'] for r in rows))

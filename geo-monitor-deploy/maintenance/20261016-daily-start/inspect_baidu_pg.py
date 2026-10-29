import json
import subprocess

def query(sql):
    return json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',
        "select coalesce(json_agg(t),'[]') from ("+sql+")t"],text=True))
print(json.dumps({'run_groups':query("select day,coalesce(payload->>'capture_mode','missing') mode,status,count(*) from monitor_runs where model_id='wenxin' and day='2026-10-16' group by 1,2,3"),
                  'recent':query("select run_id,question,payload->>'capture_mode' mode,payload->>'source_capture_complete' complete,payload->>'card_available' card,payload->>'product_review_status' review from monitor_runs where model_id='wenxin' and day='2026-10-16' order by sequence_no desc limit 7")},ensure_ascii=False))

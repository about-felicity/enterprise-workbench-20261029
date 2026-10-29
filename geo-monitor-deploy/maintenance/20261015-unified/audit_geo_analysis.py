"""Read-only product grounding, answer fidelity and dashboard-count audit."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0,'/opt/monitor')
import save_doubao_refs as saver
from monitor_core.ingestion import clean_deepseek_answer


def rows(sql):
    text=subprocess.check_output(['docker','exec','monitor-postgres','psql','-X','-qAt','-v','ON_ERROR_STOP=1','-U','monitor_app','-d','monitor','-c',
        "BEGIN READ ONLY;SET LOCAL statement_timeout='30s';SELECT coalesce(json_agg(t),'[]') FROM ("+sql+")t;COMMIT;"],text=True,timeout=45)
    return json.loads(text)


report={'at':time.time()}
products=rows("SELECT r.model_id,r.run_id,r.day,r.answer,r.payload->>'product_review_status' review_status,coalesce((select json_agg(p.payload order by p.product_index) from monitor_products p where p.model_id=r.model_id and p.run_id=r.run_id),'[]') products FROM monitor_runs r WHERE r.day>='2026-10-13' AND r.status='success' AND r.payload->>'product_review_status'='ai_verified'")
failed=[];verified=Counter();product_count=0
for row in products:
    try:saver.validate_grounded_ai_products(row['answer'],row['products'])
    except ValueError as error:failed.append({'model':row['model_id'],'run_id':row['run_id'],'day':row['day'],'reason':str(error)})
    else:verified[row['model_id']]+=1;product_count+=len(row['products'])
report['product_grounding']={'verified_answers':dict(verified),'verified_product_rows':product_count,'failed':failed,
    'scope':'Stored ai_verified product evidence/name grounding and negation checks; not a claim of perfect semantic classification.'}
events=rows("SELECT e.request_id,e.model_id,e.record,r.answer FROM monitor_ingest_events e JOIN monitor_runs r ON e.model_id=r.model_id AND e.run_id=r.run_id WHERE e.received_at>=now()-interval '1 day'")
body_diffs=[]
for row in events:
    record=row['record'];raw=record.get('answerText',record.get('web_body',''))
    expected=clean_deepseek_answer(raw) if row['model_id']=='deepseek' else raw
    if expected!=row['answer']:body_diffs.append({'request_id':row['request_id'],'model':row['model_id'],'raw_length':len(raw),'stored_length':len(row['answer'])})
report['body_fidelity']={'records_checked':len(events),'mismatches':body_diffs}
report['analysis_status']=rows("SELECT model_id,coalesce(payload->>'product_review_status','unset') status,count(*) answers FROM monitor_runs WHERE day='2026-10-15' AND status='success' GROUP BY model_id,payload->>'product_review_status'")
baseline=rows("SELECT model_id,count(*) answers FROM monitor_runs WHERE day='2026-10-13' AND status='success' AND btrim(answer)<>'' AND coalesce(payload->>'body_capture_complete','true')<>'false' AND coalesce(payload->>'source_capture_complete','true')<>'false' AND NOT (model_id='wenxin' AND coalesce(payload->>'source_capture_complete','')='true' AND NOT EXISTS(SELECT 1 FROM monitor_sources s WHERE s.model_id=monitor_runs.model_id AND s.run_id=monitor_runs.run_id)) AND question NOT LIKE '成都做GEO比较好的公司推荐一下%' GROUP BY model_id")
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
    with opener.open('http://127.0.0.1:8765/api/analytics?date=2026-10-13&view=brands',timeout=45) as stream:analytics=json.load(stream)
    report['historical_dashboard_counts']={'database':baseline,'api':[{k:m.get(k) for k in ('id','runs','product_analysis_pending_runs')} for m in analytics.get('models',[])],
                                         'payload_keys':list(analytics),'filters':analytics.get('filters'), 'same_production_completeness_scope':True}
except Exception as error:report['historical_dashboard_counts']={'error_kind':type(error).__name__}
report['passed_structural_checks']=not failed and not body_diffs
target=Path('/opt/monitor/geo-capture/maintenance/20261015-unified/analysis-audit.json')
target.write_text(json.dumps(report,ensure_ascii=False,indent=2));target.chmod(0o600)
print(json.dumps(report,ensure_ascii=False))

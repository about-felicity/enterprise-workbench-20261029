import json,shutil,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
from geo_source_cards.api_budget import INPUT_MISS,OUTPUT
from geo_source_cards.runtime import atomic_json
root=runtime.job_root('creation-1793349986-2d78d298')
audit=Path('/opt/monitor/geo-content/maintenance/recovery-20261031/whitening-http.json')
assert not audit.exists(),'Recovery already issued'
failure=recovery.http_failure(root)
assert failure and failure['retry_available'] and failure['http_status']==[502]
active=runtime.read(root/'api/active.json');ticket=runtime.read(root/'queue'/active['ticket']/'ticket.json');job=runtime.read(root/'job.json')
budget=runtime.SharedBudget(root)
try:remaining=budget.remaining(ticket['meta'],ticket['stage'])
finally:budget.db.close()
upper=0
for call in failure['calls']:
 payload=runtime.read((root/call['path']).parent/'request.json')
 upper+=(len(json.dumps(payload['messages'],ensure_ascii=False).encode('utf8'))+256)*INPUT_MISS/1000000+payload['max_tokens']*OUTPUT/1000000
assert remaining is not None and remaining>=upper,(remaining,upper)
atomic_json(audit,{'at':time.time(),'original_active':active,'original_ticket':ticket,'failure':failure,'budget':job['budget_limits'],'remaining':remaining,'estimated_retry_upper':upper,'original_reservations_preserved':True,'authorization':'REDACTED_CONFIGURE_LOCALLY'})
replacement=recovery.recover_http_failure(root)
assert replacement
runtime.resume(root,check_balance=False)
atomic_json(audit,{**runtime.read(audit),'replacement':replacement,'status':'resumed'})
print('HTTP_RECOVERED',json.dumps({'replacement':replacement,'remaining':remaining,'estimated_upper':upper,'limits':job['budget_limits']},ensure_ascii=False))

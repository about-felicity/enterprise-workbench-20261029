import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
from geo_source_cards.api_budget import INPUT_MISS,OUTPUT
from geo_source_cards.runtime import atomic_json
allowed={'plan-c9017fa6d4684997a3370eaf9fc5a553','plan-47fbabcdee8c4807a4f895016f830dbc'}
for p in (runtime.BASE/'runs').glob('*/job.json'):
 job=runtime.read(p);root=p.parent
 if job.get('date')!='2026-10-31' or job.get('studio_plan_id') not in allowed:continue
 failure=recovery.http_failure(root)
 if not failure or not failure['retry_available']:continue
 audit=Path('/opt/monitor/geo-content/maintenance/recovery-20261031')/(root.name+'-http.json')
 if audit.exists():continue
 active=runtime.read(root/'api/active.json');ticket=runtime.read(root/'queue'/active['ticket']/'ticket.json')
 budget=runtime.SharedBudget(root)
 try:remaining=budget.remaining(ticket['meta'],ticket['stage'])
 finally:budget.db.close()
 upper=0
 for call in failure['calls']:
  payload=runtime.read((root/call['path']).parent/'request.json')
  upper+=(len(json.dumps(payload['messages'],ensure_ascii=False).encode('utf8'))+256)*INPUT_MISS/1000000+payload['max_tokens']*OUTPUT/1000000
 if remaining is None or remaining<upper:
  print('BUDGET_BLOCKED',json.dumps({'job':root.name,'question':job['question'],'remaining':remaining,'upper':upper,'limits':job['budget_limits']},ensure_ascii=False),flush=True);continue
 atomic_json(audit,{'at':time.time(),'original_active':active,'original_ticket':ticket,'failure':failure,'budget':job['budget_limits'],'remaining':remaining,'estimated_retry_upper':upper,'original_reservations_preserved':True,'authorization':'REDACTED_CONFIGURE_LOCALLY'})
 replacement=recovery.recover_http_failure(root);assert replacement
 runtime.resume(root,check_balance=False)
 atomic_json(audit,{**runtime.read(audit),'replacement':replacement,'status':'resumed'})
 print('HTTP_RECOVERED',json.dumps({'job':root.name,'question':job['question'],'remaining':remaining,'upper':upper,'replacement':replacement},ensure_ascii=False),flush=True)

for p in (runtime.BASE/'runs').glob('*/job.json'):
 job=runtime.read(p);root=p.parent
 if job.get('date')!='2026-10-31' or job.get('studio_plan_id')!='plan-4c988f3863344f52aff3aa2b1f96beb2' or job.get('preparation')!='insufficient':continue
 exclusion=runtime.read(root/'off_topic_source_exclusions.json')
 print('SPRAY_FILTER',json.dumps({'question':job['question'],'off_topic':exclusion.get('excluded_count'),'examples':exclusion.get('sources',[])[:3]},ensure_ascii=False),flush=True)

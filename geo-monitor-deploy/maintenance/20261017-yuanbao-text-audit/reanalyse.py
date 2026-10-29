"""Bounded repair through the existing paid, grounded reviewer and rate budget."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0,'/app')
import save_doubao_refs as saver
import remote_product_ai_worker as worker
from monitor_core.database import connection,pending_product_runs,verified_product_runs,update_product_analysis,defer_product_analysis
from monitor_core.product_analysis import build_knowledge,batch_model_review,deterministic_review

ROOT=Path('/app/geo-capture/maintenance/20261017-yuanbao-text-audit')
LIMITS=json.loads((ROOT/'review-limits.json').read_text())
hourly=int(LIMITS['REMOTE_PRODUCT_AI_CALLS_PER_HOUR'])
batch=int(LIMITS['REMOTE_PRODUCT_AI_MODEL_BATCH'])
assert 1<=batch<=12 and 1<=hourly<=120
assert worker.acquire_lock(),'Existing analysis owner must finish; never run duplicate paid workers'
calls=0;verified=0;start=time.time();last_error=None
def remaining():
 with connection() as conn:
  rows=conn.execute("SELECT day,count(*) n FROM monitor_runs WHERE payload->>'product_extraction_method'='pending_native_text_repair' AND payload->>'product_review_status'='ai_pending' GROUP BY day").fetchall()
 return {str(r['day']):r['n'] for r in rows}
def state(status,**extra):
 value={'status':status,'time':time.time(),'started':start,'calls':calls,'verified':verified,'remaining':remaining(),**extra}
 path=ROOT/'reanalysis-status.json';temporary=path.with_suffix('.tmp');temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2));temporary.replace(path)
 print(json.dumps(value,ensure_ascii=False),flush=True)
try:
 knowledge=build_knowledge(verified_product_runs())
 state('running')
 while time.time()-start<3600 and calls<90:
  left=remaining()
  if not left:state('complete');break
  rows=pending_product_runs(100,max_retries=10,days=['2026-10-15','2026-10-16','2026-10-17'])
  rows=[r for r in rows if r.get('product_extraction_method')=='pending_native_text_repair' or (str(r.get('day'))=='2026-10-17')]
  if not rows:
   state('waiting_existing_retry_window')
   time.sleep(30);continue
  paid=[]
  for run in rows[:batch]:
   try:
    rule=saver.extract_products(run['answer'])
    products,method=deterministic_review(run['answer'],run['question'],knowledge,rule,saver.numbered_product_block_count(run['answer']))
    if products is not None and method=='verified_answer_reuse':
     saver.validate_grounded_ai_products(run['answer'],products)
     update_product_analysis(run['model_id'],run['run_id'],products,'ai_verified','deterministic-v1',method)
     verified+=1;continue
   except (KeyError,ValueError):pass
   paid.append({**run,'id':str(len(paid)),'full_context':True})
  if not paid:state('running');continue
  if not worker.reserve_hourly_slots(1,hourly):state('waiting_existing_hourly_budget');time.sleep(30);continue
  calls+=1
  try:
   results,usage=batch_model_review(paid,knowledge)
   for item in paid:
    products=results.get(item['id'])
    if products is None:
     defer_product_analysis(item['model_id'],item['run_id'],int(LIMITS['REMOTE_PRODUCT_AI_RETRY_DELAY']))
     continue
    update_product_analysis(item['model_id'],item['run_id'],products,'ai_verified',usage.get('model',''),'llm_batch_grounded_native_text_repair')
    verified+=1
   state('running',usage=usage)
  except Exception as error:
   # Keep uncertain results pending, observe the provider's normal cool-down.
   last_error=type(error).__name__
   state('provider_retry',error_type=last_error)
   if worker.provider_unavailable_error(error):break
   time.sleep(30)
  time.sleep(2)
 else:state('bounded_run_finished',error_type=last_error)
finally:
 if worker.LOCK.exists() and worker.LOCK.read_text().strip()==worker.process_lock_token():worker.LOCK.unlink()

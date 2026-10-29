"""Upgrade only known UNSENT writer requests using a smaller lossless prompt."""
import hashlib,json,shutil,time
from pathlib import Path
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.rewrite_v2 import full_writer
from geo_source_cards.rewrite_v2.common import cache_root
from geo_source_cards.deepseek_api import request_payload
from geo_source_cards.api_budget import INPUT_MISS,OUTPUT

def recover(root):
 with process_lock(root/'coordinator.lock',blocking=False):
  current=runtime.read(root/'api/active.json')
  if current and current.get('state')!='SUBMITTED':return None
  for path in (root/'queue').glob('*/ticket.json'):
   job=runtime.read(path);receipt=runtime.read(path.parent/'receipt.json')
   if job.get('stage')!='writer' or job.get('state')!='needs_attention' or receipt.get('error_code')!='article_budget_exceeded':continue
   if job.get('meta',{}).get('workflow')!='rewrite-v2':continue
   run=root/'api/runs'/job['execution']['run_id'];proof=runtime.read(run/'preflight_rejection.json')
   if proof.get('request_sent') is not False or proof.get('reason')!='article_budget_exceeded':continue
   if (run/'call/api_state.json').exists() or (run/'call/response.json').exists():continue
   if receipt['execution']!=job['execution']:raise ValueError('Execution mismatch')
   for name,digest in job['inputs'].items():
    if hashlib.sha256((run/name).read_bytes()).hexdigest()!=digest:raise ValueError('Immutable input changed')
   backups=root/'maintenance/unsent-budget'/job['id']
   if backups.exists():continue
   context=runtime.read(run/'rewrite_context.json')
   materials=[runtime.read(p) for p in (cache_root(root)/'material').glob('*.json')]
   material=next(v for v in materials if v['raw_product']==context['product'])
   class Capture:
    def complete(self,prompt,directory,**kwargs):
     self.payload=request_payload(prompt,kwargs['max_tokens']);self.payload['temperature']=kwargs['temperature']
     return {'draft_markdown':'# Offline budget calculation'}
   budget=runtime.SharedBudget(root)
   try:
    capture=Capture();capture.budget=budget
    full_writer.generate(capture,context,material,run/'call',job['meta'],
     previous=(run/'draft.md').read_text() if (run/'draft.md').exists() else None,
     feedback=runtime.read(run/'rewrite_feedback.json') if (run/'rewrite_feedback.json').exists() else None)
    upper=(len(json.dumps(capture.payload['messages'],ensure_ascii=False).encode())+256)*INPUT_MISS/1000000+capture.payload['max_tokens']*OUTPUT/1000000
    remaining=budget.remaining(job['meta'],'writer')
   finally:budget.db.close()
   if remaining is None or upper>remaining:continue
   backups.mkdir(parents=True)
   for p in [path,path.parent/'receipt.json',run/'preflight_rejection.json']:shutil.copy2(p,backups/p.name)
   (path.parent/'receipt.json').rename(backups/'original-failed-receipt.json')
   marker=path.parent/'auto_repair_blocked.json'
   if marker.exists():marker.rename(backups/marker.name)
   if current:
    destination=root/'api/history'/(current['run_id']+'.json');destination.parent.mkdir(parents=True,exist_ok=True)
    (root/'api/active.json').replace(destination)
   atomic_json(path,{k:v for k,v in {**job,'state':'claimed'}.items() if k!='error'})
   atomic_json(root/'api/active.json',{'ticket':job['id'],'run_id':job['execution']['run_id'],'state':'REQUESTING',
    'stage':'writer','execution':job['execution'],'started_epoch':time.time()})
   atomic_json(backups/'reconciliation.json',{'at':time.time(),'known_unsent':True,'same_execution':job['execution'],
    'remaining_cny':remaining,'new_upper_bound_cny':upper,'budget_increased':False,'rewrite_round':job['meta'].get('rewrite_round',0),
    'reason':'Lossless factoring of repeated source metadata; no draft or paid call exists at this request path'})
   return job['id']
 return None

"""Continue the same second revision after a parser-only heading correction."""
import sys,time,json,shutil,hashlib,traceback
from pathlib import Path
R=Path('/opt/monitor/geo-content/runtime/acceptance/20261022-three-agent')
sys.path[:0]=[str(R/'stage'),str(R/'stage/engine')]
from creation import runtime
from creation.client import CreationClient
from geo_source_cards import section_writer
from geo_source_cards.api_worker import Worker
from geo_source_cards.runtime import process_lock,atomic_json
from geo_source_cards.deepseek_api import APIError
from geo_source_cards.pipeline_control import pause

def main():
 with process_lock(R/'runner.lock',blocking=False),process_lock(R/'api/worker.lock',blocking=False):
  marker=R/'known-heading-continuation.json';assert not marker.exists(),'Inspect durable continuation; do not rerun'
  tid='6d006a094c390080dd0bf67c';folder=R/'queue'/tid;job=runtime.read(folder/'ticket.json');run=R/'api/runs'/job['execution']['run_id']
  assert job['state']=='needs_attention' and job['meta']['compiled_repair_round']==2
  assert runtime.read(folder/'receipt.json')['error_code']=='section_generation_exhausted'
  assert runtime.read(run/'section_calls/manifest.json')['failed_component']=='S1'
  assert not runtime.read(R/'api/active.json')
  for name,expected in job['inputs'].items():assert hashlib.sha256((R/job['location']/name).read_bytes()).hexdigest()==expected
  for p in run.rglob('api_state.json'):
   state=runtime.read(p);assert state.get('state') not in {'REQUESTING','REQUEST_UNKNOWN'},'Unknown intent cannot be replayed'
  auth=runtime.read(R/'authorization.json');old=auth['original_settings'];changed=auth['leased_settings']
  atomic_json(marker,{'at':time.time(),'ticket':tid,'run':run.name,'same_execution':job['execution'],'content_revision':2,'additional_content_revision':False,'reason':'Saved section title/heading normalization; raw responses retained'})
  shutil.copytree(folder,R/'repair_evidence/heading-parser-continuation/ticket')
  (folder/'receipt.json').rename(folder/'failed-before-heading-recovery.json')
  job={**job,'state':'claimed'};atomic_json(folder/'ticket.json',job)
  active={'ticket':tid,'run_id':run.name,'state':'REQUESTING','stage':'writer','started_epoch':time.time(),'execution':job['execution']}
  atomic_json(R/'api/active.json',active)
  with process_lock(runtime.SHARED/'settings.lock',blocking=True):
   now=runtime.read(runtime.SHARED/'settings.json');assert all(now[k]==old[k] for k in ('article_budget_cny','daily_budget_cny'))
   atomic_json(runtime.SHARED/'settings.json',{**now,**{k:changed[k] for k in ('article_budget_cny','daily_budget_cny')}})
  budget=runtime.SharedBudget(R);client=CreationClient(runtime.KEY,budget=budget);worker=Worker(R,client,target_article=('2026-10-21','排行类',1))
  result={}
  try:
   atomic_json(R/'status.json',{'at':time.time(),'state':'running','stage':'known_heading_continuation','run_id':run.name})
   answer=section_writer.generate(client,run,job['meta']);atomic_json(run/'answer.json',answer)
   active['state']='RESPONDED';atomic_json(R/'api/active.json',active)
   result=worker.finish(job,active)
   print(json.dumps(result,ensure_ascii=False),flush=True)
   # Only normal follow-on review, never a third content revision.
   if result['status']=='accepted':
    for step in range(4):
     result=worker.once('2026-10-21');print(json.dumps(result,ensure_ascii=False),flush=True)
     if result['status'] in {'idle','completed_with_failures','needs_attention'} or result['status'].startswith('blocked'):break
  except APIError as e:
   if e.uncertain:pause(R,'unknown_request','已保留未知请求，禁止重发');result={'status':'request_unknown','code':e.code}
   elif e.code=='section_generation_exhausted':result=worker.failed(job,active,e.code)
   else:pause(R,'acceptance_stopped','保留已收到答复与预算阻断');result={'status':'blocked','code':e.code}
  except BaseException as e:
   pause(R,'acceptance_stopped','保留执行状态，不自动重发');result={'status':'blocked','type':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc()[-3000:]}
  finally:
   client.close();budget.close()
   with process_lock(runtime.SHARED/'settings.lock',blocking=True):
    now=runtime.read(runtime.SHARED/'settings.json')
    for k in ('article_budget_cny','daily_budget_cny'):
     if now[k]==changed[k]:now[k]=old[k]
    atomic_json(runtime.SHARED/'settings.json',now)
   atomic_json(R/'heading-recovery-result.json',{'at':time.time(),'result':result})
   atomic_json(R/'status.json',{'at':time.time(),'state':'heading_continuation_finished','result':result})
   print(json.dumps(result,ensure_ascii=False),flush=True)

if __name__=='__main__':main()

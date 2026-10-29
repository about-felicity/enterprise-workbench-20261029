"""Reconcile a known paid table response; never resend or alter its contents."""
import hashlib,json,os,shutil,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;os.environ['GEO_CREATION_ROOT']=str(B/'runtime')
sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.deepseek_api import DeepSeekClient
from geo_source_cards.rewrite_v2 import material_manager
from geo_source_cards.rewrite_v2.common import cache_root
s=runtime.read(B/'state.json');root=runtime.job_root(s['job_id'])
class Offline:
 def post(self,*a,**k):raise AssertionError('Recovery must not send any request')
 def get(self,*a,**k):raise AssertionError('Recovery must not send any request')
with process_lock(B/'acceptance.lock',blocking=False),process_lock(root/'coordinator.lock',blocking=False):
 active=runtime.read(root/'api/active.json');ticket=root/'queue'/active['ticket'];job=runtime.read(ticket/'ticket.json');receipt=runtime.read(ticket/'receipt.json');run=root/'api/runs'/active['run_id']
 assert active['state']=='SUBMITTED' and job['stage']=='writer' and job['state']=='needs_attention'
 assert job['meta']['workflow']=='rewrite-v2' and not job['meta'].get('rewrite_round')
 assert receipt['state']=='failed' and receipt['error_code']=='rewrite_v2_invalid_output' and receipt['detail'].startswith('Material contains a quote absent from original:')
 assert receipt['execution']==active['execution']==job['execution']
 assert not (run/'call/api_state.json').exists() and not (run/'call/response.json').exists() and not (run/'draft.md').exists()
 for name,digest in job['inputs'].items():assert hashlib.sha256((run/name).read_bytes()).hexdigest()==digest
 calls=list(run.rglob('api_state.json'));assert len(calls)==1 and calls[0].parent.name=='material-call' and runtime.read(calls[0])['state']=='RESPONDED'
 raw=run/'material-call/response.json';before=hashlib.sha256(raw.read_bytes()).hexdigest()
 context=runtime.read(run/'rewrite_context.json')
 result=material_manager.process(DeepSeekClient(runtime.KEY,session=Offline()),context['product'],cache_root(root),run/'material-call',job['meta'])
 assert hashlib.sha256(raw.read_bytes()).hexdigest()==before
 backup=root/'maintenance/known-table-whitespace';backup.mkdir(parents=True,exist_ok=False)
 for path in [ticket/'ticket.json',ticket/'receipt.json',root/'api/active.json']:
  shutil.copy2(path,backup/path.name)
 (ticket/'receipt.json').rename(backup/'original-failed-receipt.json')
 marker=ticket/'auto_repair_blocked.json'
 if marker.exists():marker.rename(backup/marker.name)
 atomic_json(ticket/'ticket.json',{k:v for k,v in {**job,'state':'claimed'}.items() if k!='error'})
 atomic_json(root/'api/active.json',{**active,'state':'REQUESTING'})
 atomic_json(backup/'reconciliation.json',{'at':time.time(),'reason':'Whitespace-only table projection verified against exact original spans',
  'paid_response_sha256':before,'material_sha256':result['sha256'],'extra_api_calls':0,'same_execution':active['execution'],'full_drafts_before_recovery':0})
print(json.dumps({'recovered':active['ticket'],'extra_api_calls':0,'raw_paid_response_unchanged':True}))

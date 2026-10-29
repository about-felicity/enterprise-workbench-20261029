import hashlib,json,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.staged_editorial import read
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.rewrite_v2.common import text_hash
root=B/'runtime/runs'/read(B/'state.json')['job_id'];proof=root/'maintenance/source-once-v1.json'
with process_lock(B/'acceptance.lock',blocking=False):
 assert read(root/'control.json')['paused']
 assert not any(read(p).get('state') in {'REQUESTING','REQUEST_UNKNOWN'} for p in (root/'api').rglob('api_state.json'))
 if proof.exists():print(json.dumps(read(proof)));raise SystemExit(0)
 changes=[]
 for path in sorted((root/'queue').glob('*/ticket.json')):
  t=read(path)
  if t['state']!='needs_attention':continue
  receipt=read(path.parent/'receipt.json')
  archive=root/'maintenance/source-once-inputs'/t['id'];archive.mkdir(parents=True,exist_ok=True)
  atomic_json(archive/'ticket.json',t);atomic_json(archive/'receipt.json',receipt)
  if t['stage']=='review' and receipt.get('error_code')=='article_budget_exceeded':
   run=root/'api/runs'/t['execution']['run_id'];preflight=read(run/'preflight_rejection.json')
   assert preflight.get('request_sent') is False and preflight['reason']=='article_budget_exceeded'
   assert not list((run/'review-calls').rglob('api_state.json')) and not list((run/'review-calls').rglob('response.json'))
   assert receipt['execution']==t['execution']
   for name,digest in t['inputs'].items():assert hashlib.sha256((run/name).read_bytes()).hexdigest()==digest
   atomic_json(archive/'preflight_rejection.json',preflight)
   location=root/t['location'];meta={**t['meta'],'source_projection_version':'source-once-v1'}
   action='known_unsent_review_with_source_deduplication'
  elif t['stage']=='writer' and receipt.get('error_code')=='rewrite_v2_invalid_output':
   location=(root/t['location']).parent/'review';result=read(location/'result.json')
   assert result['draft_sha256']==text_hash(((root/t['location'])/'draft.md').read_text('utf8'))
   atomic_json(archive/'review.json',result)
   parent=read(root/'queue'/t['meta']['replaces']/'ticket.json');assert parent['stage']=='review'
   meta={**parent['meta'],'review_projection_from':str((archive/'review.json').relative_to(root)),
         'decision_rules_revision':'source-once-v1'}
   action='zero_call_reassessment_of_noop_repair'
  else:raise AssertionError('Unexpected unresolved ticket: '+t['id'])
  replacement=publish_ticket(root,'review',location,
   ['rewrite_context.json','rewrite_material.json','draft.md','product.json','category.json'],['result.json'],
   {**meta,'revision':int(t['meta'].get('revision',0))+1,'replaces':t['id']})
  atomic_json(path,{**t,'state':'revision_requested','replaced_by':replacement,'superseded_reason':action})
  changes.append({'old_ticket':t['id'],'new_ticket':replacement,'action':action})
 atomic_json(proof,{'at':time.time(),'same_job_and_cost_scopes':True,'changes':changes})
 print(json.dumps(read(proof),ensure_ascii=False,indent=2))

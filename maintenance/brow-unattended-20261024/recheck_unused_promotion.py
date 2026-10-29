import json,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.staged_editorial import read
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.rewrite_v2.common import verify,text_hash
from geo_source_cards.rewrite_v2.quality_reviewer import adjudicate
root=B/'runtime/runs'/read(B/'state.json')['job_id']
with process_lock(B/'acceptance.lock',blocking=False):
 for path in sorted((root/'queue').glob('*/ticket.json')):
  t=read(path)
  if t['stage']!='review' or t['state']!='needs_attention':continue
  location=root/t['location'];r=verify(read(location/'result.json'));c=read(location/'rewrite_context.json')
  draft=(location/'draft.md').read_text('utf8');assert r['draft_sha256']==text_hash(draft)
  assert not adjudicate(r['raw_evidence_report'],c,draft)[0]['findings']
  archive=root/'maintenance/unused-promotion'/t['id'];archive.mkdir(parents=True,exist_ok=True)
  atomic_json(archive/'review.json',r);atomic_json(archive/'ticket.json',t)
  replacement=publish_ticket(root,'review',location,list(t['inputs']),t['outputs'],
   {**t['meta'],'review_projection_from':str((archive/'review.json').relative_to(root)),
    'decision_rules_revision':'unused-promotion-v1','revision':int(t['meta'].get('revision',0))+1,'replaces':t['id']})
  atomic_json(path,{**t,'state':'revision_requested','replaced_by':replacement,
      'superseded_reason':'Deterministic source-price comparison; no new model call or article edit'})
  print(json.dumps({'old':t['id'],'new':replacement,'new_paid_calls':0}))

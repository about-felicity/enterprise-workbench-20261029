"""Reapply deterministic evidence rules to saved reviews without paid rereview."""
import json, shutil, sys, time
from pathlib import Path
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from geo_source_cards.staged_editorial import read
from geo_source_cards.runtime import atomic_json, process_lock
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.rewrite_v2 import integration
from geo_source_cards.rewrite_v2.common import text_hash, verify
root=B/'runtime/runs'/read(B/'state.json')['job_id'];proof=root/'maintenance/evidence-rules-v1.json'
with process_lock(B/'acceptance.lock',blocking=False):
    assert read(root/'control.json')['paused']
    assert not any(read(p).get('state') in {'REQUESTING','REQUEST_UNKNOWN'} for p in (root/'api').rglob('api_state.json'))
    if proof.exists():print(json.dumps(read(proof)));raise SystemExit(0)
    changes=[]
    for path in sorted((root/'queue').glob('*/ticket.json')):
        t=read(path)
        if t['stage']=='review' and t['state']=='needs_attention' and read(path.parent/'receipt.json').get('error_code')=='output_incomplete':
            integration.handle_failure(root,t,'Known completed response was truncated; one bounded larger-output review permitted')
            changes.append({'ticket':t['id'],'action':'known_truncated_response_retry','new_ticket':read(path)['replaced_by']})
        if t['stage']!='writer' or t['state']!='pending' or t['meta'].get('repair_mode')!='exact-span-v1':continue
        assert not (path.parent/'receipt.json').exists() and not t.get('execution')
        parent=read(root/'queue'/t['meta']['replaces']/'ticket.json')
        assert parent['stage']=='review'
        location=root/parent['location'];result=verify(read(location/'result.json'))
        writer=root/t['location'];draft=(writer/'draft.md').read_text('utf8')
        assert result['draft_sha256']==text_hash(draft)
        archive=root/'maintenance/evidence-rules-inputs'/t['id'];archive.mkdir(parents=True,exist_ok=True)
        atomic_json(archive/'pending_ticket.json',t);atomic_json(archive/'review.json',result)
        replacement=publish_ticket(root,'review',location,list(parent['inputs']),parent['outputs'],
            {**parent['meta'],'review_projection_from':str((archive/'review.json').relative_to(root)),
             'decision_rules_revision':'evidence-rules-v1','revision':int(t['meta'].get('revision',0))+1,'replaces':t['id']})
        atomic_json(path,{**t,'state':'revision_requested','replaced_by':replacement,
            'superseded_reason':'Unsent repair suspended; deterministic adjudication of preserved review first'})
        changes.append({'ticket':t['id'],'action':'offline_saved_review_projection','new_ticket':replacement,
                        'completed_targeted_repairs':parent['meta'].get('targeted_repair_round',0),'new_paid_calls':0})
    atomic_json(proof,{'at':time.time(),'changes':changes,'same_job_and_budget':True})
    print(json.dumps(read(proof),ensure_ascii=False,indent=2))

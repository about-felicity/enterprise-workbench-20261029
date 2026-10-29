"""Reassess the same seven drafts under the explicitly authorized new policy.

No article, full-rewrite counter, budget, execution receipt or paid call is reset.
"""
import json, shutil, sys, time
from pathlib import Path
B = Path(__file__).resolve().parent
sys.path[:0] = [str(B/'release/engine'), str(B/'release')]
from geo_source_cards.runtime import atomic_json, process_lock
from geo_source_cards.staged_editorial import read
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.rewrite_v2.common import verify
state = read(B/'state.json'); root = B/'runtime/runs'/state['job_id']
proof = root/'maintenance/evidence-v3-migration.json'
authorization = '2026-10-24 用户确认：措辞偏好不拦截，修正事实错误、上线七问题每日计划并实际验证；用户答复“对，开始”。'
with process_lock(B/'acceptance.lock', blocking=False):
    if proof.exists():
        print(json.dumps(read(proof), ensure_ascii=False)); raise SystemExit(0)
    assert not any(read(p).get('state') == 'REQUESTING' for p in (root/'api').rglob('api_state.json'))
    original_policy = read(root/'rewrite_policy.json')
    atomic_json(root/'maintenance/rewrite_policy.before-evidence-v3.json', original_policy)
    atomic_json(root/'rewrite_policy.json', {**original_policy, 'review_policy':'evidence-v3',
        'max_targeted_repairs':2, 'review_policy_authorization':authorization})
    migrated = []
    for path in sorted((root/'queue').glob('*/ticket.json')):
        job = read(path)
        if job['stage'] != 'review' or job['state'] != 'needs_attention': continue
        location = root/job['location']; result = verify(read(location/'result.json'))
        assert result['pass'] is False and result.get('review_protocol') != 'evidence-v3'
        archive = root/'maintenance/pre-evidence-v3'/job['id']; archive.mkdir(parents=True, exist_ok=True)
        for source in (path, path.parent/'receipt.json', location/'result.json'):
            assert source.is_file(); shutil.copy2(source, archive/source.name)
        replacement = publish_ticket(root, 'review', location,
            ['rewrite_context.json','rewrite_material.json','draft.md','product.json','category.json'], ['result.json'],
            {**job['meta'], 'review_policy_revision':'evidence-v3', 'revision': int(job['meta'].get('revision',0))+1,
             'replaces':job['id']})
        atomic_json(path, {**job, 'state':'revision_requested', 'replaced_by':replacement,
            'superseded_reason':'User-authorized review policy correction; same article and cumulative budget'})
        migrated.append({'old_ticket':job['id'], 'new_review_ticket':replacement,
                         'full_rewrites_already_used':job['meta'].get('rewrite_round',0)})
    assert len(migrated) == 7
    atomic_json(proof, {'at':time.time(), 'authorization':authorization, 'same_job_id':root.name,
        'new_full_rewrites':0, 'budget_unchanged':True, 'tickets':migrated})
    print(json.dumps(read(proof), ensure_ascii=False, indent=2))

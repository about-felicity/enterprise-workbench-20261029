"""Record the user's explicit approval of the previously shown sample skeleton."""
from run_sample import BASE, ROOT, CACHE
from geo_source_cards.runtime import atomic_json, process_lock
from geo_source_cards.staged_editorial import read
from geo_source_cards.rewrite_v2 import structure_parser, integration

inspected = read(BASE / 'skeleton-inspected.json')
proposed = read(BASE / 'skeleton-proposed.json')
value = structure_parser.approve(CACHE, inspected['cache_key'], inspected['sha256'],
                                'user: 可以继续 (2026-10-23)', skeleton=proposed)
atomic_json(ROOT / 'skeleton-user-confirmation.json', {
    'request': '我先看看再看下一步', 'subsequent_confirmation': '可以继续',
    'reviewed_file': 'outputs/rewrite-v2-real-sample-20261023/skeleton-review.md',
    'approved_skeleton_sha256': value['approval']['skeleton_sha256']})
with process_lock(ROOT / 'coordinator.lock', blocking=True):
    integration.sync_approvals(ROOT)
print('User approval recorded; original queue continued with the reviewed skeleton.')

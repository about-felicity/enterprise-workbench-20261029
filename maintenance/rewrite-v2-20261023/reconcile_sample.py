"""Revalidate the single known completed parser response with zero network access."""
import json
from pathlib import Path
import shutil
from run_sample import ROOT, BASE, DAY
from geo_source_cards.api_worker import Worker
from geo_source_cards.deepseek_api import DeepSeekClient
from geo_source_cards.runtime import atomic_json, process_lock
from geo_source_cards.staged_editorial import read
from creation.runtime import KEY

class Offline:
    def get(self, *args, **kwargs): raise AssertionError('Network forbidden during reconciliation')
    def post(self, *args, **kwargs): raise AssertionError('Network forbidden during reconciliation')

worker = Worker(ROOT, DeepSeekClient(KEY, session=Offline()))
active = read(ROOT / 'api/active.json')
ticket = ROOT / 'queue' / active['ticket']
job = read(ticket / 'ticket.json')
receipt = read(ticket / 'receipt.json')
run = ROOT / 'api/runs' / active['run_id']
assert job['stage'] == 'research' and job['state'] == 'needs_attention'
assert receipt['error_code'] == 'rewrite_v2_invalid_output'
assert receipt['detail'] == 'Incomplete semantic skeleton schema'
assert read(run / 'skeleton-call/api_state.json')['state'] == 'RESPONDED'
assert read(run / 'skeleton-call/response.json')['type'] == 'json_object'
with process_lock(ROOT / 'coordinator.lock', blocking=True):
    archive = ticket / 'known-format-rejection'
    archive.mkdir(exist_ok=False)
    for name in ('ticket.json', 'receipt.json'):
        shutil.copy2(ticket / name, archive / name)
    shutil.copy2(ROOT / 'api/active.json', archive / 'active.json')
    (ticket / 'receipt.json').rename(archive / 'failed-receipt.json')
    atomic_json(ticket / 'ticket.json', {**job, 'state': 'claimed'})
    atomic_json(ROOT / 'api/active.json', {**active, 'state': 'REQUESTING'})
print(json.dumps(worker.once(DAY), ensure_ascii=False))
for path in (BASE / 'real-sample/cache/skeleton').glob('*.json'):
    shutil.copy2(path, BASE / 'real-sample/skeleton.json')
print('Reconciled original response; no new paid call; human approval still required')

"""Read-only daily Baidu coverage and full-fidelity checks, no collection."""
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import time
import sys

sys.path.insert(0, '/opt/monitor/geo-capture')
from baidu_body_delivery import verify_receipt

BASE = Path('/opt/monitor/geo-capture')
BATCH = 'geo-panel-baidu-ai-20261016-095851-ff407fd3'
root = BASE / 'batches' / BATCH
groups = {}
for batch in (BASE / 'batches').glob('geo-panel-baidu-ai-*'):
    dbpath = batch / 'collector/tasks.sqlite'
    if not dbpath.exists():
        continue
    with sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True) as db:
        for question, state, raw in db.execute('select question,state,result from captures'):
            if state != 'completed' or not raw:
                continue
            value = json.loads(raw)
            if not str(value.get('captured_at', '')).startswith('2026-10-16'):
                continue
            group = groups.setdefault(question, {'full': 0, 'body_only': 0, 'missing_or_failed': 0})
            if value.get('body_capture_complete') and str(value.get('body', '')).strip():
                group['body_only' if value.get('availability') == 'body_only' else 'full'] += 1
            else:
                group['missing_or_failed'] += 1

paths = list((root / 'body-only/receipts').glob('*.json'))
ids = [p.stem for p in paths]
assert all(len(rid) == 64 and all(c in '0123456789abcdef' for c in rid) for rid in ids)
stored = {}
if ids:
    query = "select coalesce(json_agg(json_build_object('id',request_id,'record',record,'run_id',run_id)),'[]') from monitor_ingest_events where request_id in (" + ','.join("'" + rid + "'" for rid in ids) + ')'
    stored = {r['id']: r for r in json.loads(subprocess.check_output(
        ['docker', 'exec', 'monitor-postgres', 'psql', '-U', 'monitor_app', '-d', 'monitor', '-Atc', query], text=True))}
for path in paths:
    item = json.loads((root / 'body-only/outbox' / path.name).read_text())
    verify_receipt(json.loads(path.read_text()), item)
    record = stored[path.stem]['record']
    assert stored[path.stem]['run_id']
    for field in ('web_body', 'sources', 'source_capture_complete', 'body_capture_complete', 'capture_result',
                  'batch_id', 'capture_task_id', 'round', 'card_available', 'availability'):
        assert record[field] == item['record'][field], field

report = {'at': time.time(), 'day': '2026-10-16', 'batch': BATCH, 'questions': groups,
          'questions_with_five_card_bodies': sum(g['full'] + g['body_only'] >= 5 for g in groups.values()),
          'body_only_database_fidelity': True, 'body_only_processed': len(paths),
          'supplement_health': json.loads((root / 'bridge_health.json').read_text()),
          'body_delivery_health': json.loads((root / 'body-only/health.json').read_text())}
target = BASE / 'maintenance/20261016-daily-start/baidu-today-audit.json'
target.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))

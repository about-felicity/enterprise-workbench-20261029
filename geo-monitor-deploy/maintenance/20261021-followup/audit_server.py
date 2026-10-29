"""Read-only repair, scheduling and ledger audit. Never sends paid requests."""
import hashlib
import json
import sqlite3
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path[:0] = ['/opt/monitor/geo-content', '/opt/monitor/geo-content/engine']
from geo_source_cards.consumer_prompts import require_writer_material, evidence_units

BASE = Path('/opt/monitor/geo-content')
ROOT = BASE / 'runtime/quality-repair/20261021-consumer-voice'

def read(path):
    return json.loads(path.read_text('utf-8-sig')) if path.exists() else {}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

db = sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro', uri=True)
db.row_factory = sqlite3.Row
rows = []
for item in read(ROOT / 'inventory.json')['articles']:
    entry = ROOT / item['key']
    status = read(entry / 'status.json')
    row = {k: item[k] for k in ('key', 'root', 'id', 'writer', 'research')}
    row.update(status=status, calls=[])
    for path in sorted(entry.glob('attempt-*/calls/*/api_state.json')):
        state = read(path)
        reservation = state.get('reservation')
        cost = db.execute('select * from costs where id=?', (reservation,)).fetchone() if reservation else None
        row['calls'].append({'path': str(path), 'state': state,
                             'response_exists': path.with_name('response.json').exists(),
                             'answer_exists': path.with_name('answer.json').exists(),
                             'ledger': dict(cost) if cost else None})
    writer = Path(item['writer']) if item.get('writer') else None
    try:
        if not writer:
            raise ValueError(item.get('preflight_error') or 'missing writer')
        require_writer_material(read(writer / 'knowledge.json'), read(writer / 'product.json'), evidence_units(writer))
        row['preflight'] = 'ready'
    except Exception as error:
        row['preflight'] = str(error)
    folder = Path(item['root']) / 'approved' / item['id']
    row['current_word_sha256'] = read(folder / 'receipt.json').get('word_sha256')
    row['original_word_sha256'] = item['original_word_sha256']
    row['version_unchanged'] = row['current_word_sha256'] == item['original_word_sha256']
    row['root_control'] = read(Path(item['root']) / 'control.json')
    rows.append(row)

plans = []
for path in sorted((BASE / 'studio/plans').glob('*.json')):
    p = read(path)
    days = []
    for d in sorted((BASE / 'studio/days').glob('*/' + p['plan_id'] + '.json')):
        v = read(d)
        days.append({'date': v.get('date'), 'paused': v.get('paused'), 'error': v.get('error'),
                     'status': v.get('status'), 'jobs': v.get('jobs'), 'path': str(d)})
    plans.append({**{k: p.get(k) for k in ('plan_id', 'name', 'enabled', 'frequency', 'start_date', 'execution_date', 'capture_time', 'writing_time', 'article_target', 'article_budget_cny', 'task_budget_cny')}, 'days': days})

jobs = []
for path in sorted((BASE / 'runtime/runs').glob('*/job.json')):
    p = read(path)
    days = [read(d) for d in sorted((path.parent / 'days').glob('*/day.json'))]
    jobs.append({'job': path.parent.name, 'plan': p.get('studio_plan_id'), 'date': p.get('date'),
                 'control': read(path.parent / 'control.json'),
                 'days': [{k: d.get(k) for k in ('date', 'status', 'error', 'article_target', 'shortfall')} for d in days]})
out = {'at': datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(), 'articles': rows, 'plans': plans, 'jobs': jobs,
       'states': dict(Counter(r['status'].get('state', 'pending') for r in rows)),
       'reasons': dict(Counter(r['status'].get('reason', '') for r in rows)),
       'preflight': dict(Counter(r['preflight'] for r in rows)),
       'ledger': [dict(r) for r in db.execute('select date,count(*) calls,sum(charged) charged,sum(case when charged is null then reserved else 0 end) outstanding_reserved,sum(case when charged is null then 1 else 0 end) unresolved from costs group by date order by date desc limit 3')],
       'read_only': True}
db.close()
Path('/tmp/geo-followup-audit.json').write_text(json.dumps(out, ensure_ascii=False, indent=2))
print(json.dumps({k: v for k, v in out.items() if k in ('at', 'states', 'ledger', 'read_only')}, ensure_ascii=False))
print(json.dumps({'held_ready': sum(r['status'].get('reason') == 'consumer_contract_maintenance' and r['preflight'] == 'ready' and r['version_unchanged'] for r in rows),
                  'unknown': [{'key': r['key'], 'id': r['id'], 'unresolved_calls': [c for c in r['calls'] if c['state'].get('state') == 'REQUEST_UNKNOWN']} for r in rows if r['status'].get('state') == 'unknown_request']}, ensure_ascii=False))

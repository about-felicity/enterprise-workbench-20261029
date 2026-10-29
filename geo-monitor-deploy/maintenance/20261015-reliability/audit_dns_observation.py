"""Read-only DNS incident audit; never changes capture tasks or repeats a query."""
import json
import socket
import sqlite3
import time
from pathlib import Path

base = Path('/opt/monitor/geo-capture')
pointer = json.loads((base / 'soak12h_current.json').read_text())
manifest = json.loads((Path(pointer['root']) / 'manifest.json').read_text())
batch = manifest['jobs']['baidu_ai']['batch']
path = base / 'batches' / batch / 'collector/tasks.sqlite'
report = {'at': time.time(), 'test_id': pointer['test_id'], 'batch': batch, 'incidents': []}
with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
    db.row_factory = sqlite3.Row
    for row in db.execute("select task_id,ordinal,round,state,finished,result from captures where result like '%ERR_NAME_NOT_RESOLVED%'"):
        record = json.loads(row['result'])
        attempts = [dict(x) for x in db.execute('select kind,error,epoch from search_recovery_attempts where task_id=? order by id', (row['task_id'],))]
        later = db.execute("select count(*) from captures where state='completed' and finished>? and json_extract(result,'$.body_capture_complete')=1 and json_extract(result,'$.source_capture_complete')=1", (row['finished'],)).fetchone()[0]
        report['incidents'].append({
            'task_id': row['task_id'], 'ordinal': row['ordinal'], 'round': row['round'],
            'state': row['state'], 'finished': row['finished'],
            'availability': record.get('availability'),
            'body_capture_complete': record.get('body_capture_complete'),
            'source_capture_complete': record.get('source_capture_complete'),
            'recovery_attempts': [{'kind': a['kind'], 'dns_failure': 'ERR_NAME_NOT_RESOLVED' in a['error'], 'epoch': a['epoch']} for a in attempts],
            'later_complete_observations': later,
        })
try:
    report['dns_resolves_now'] = bool(socket.getaddrinfo('www.baidu.com', 443))
except OSError as exc:
    report['dns_resolves_now'] = False
    report['dns_error_kind'] = type(exc).__name__
target = base / 'maintenance/20261015-reliability/dns-observation-audit.json'
target.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))

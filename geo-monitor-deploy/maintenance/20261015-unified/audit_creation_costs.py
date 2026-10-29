"""Read-only ledger audit; estimates are not a provider invoice or new API call."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time
base=Path('/opt/monitor/geo-capture');pointer=json.loads((base/'creation_soak_current.json').read_text())
manifest=json.loads((Path(pointer['root'])/'manifest.json').read_text())
ledger=Path('/home/user/geo-editorial/runtime-api/api/costs.sqlite')
report={'at':time.time(),'test_id':pointer['test_id'],'scope':'Existing shared ledger conservative estimates, not provider invoice. Window is reservation creation time.','jobs':[]}
def summarize(rows):
    return {'calls':len(rows),'settled_estimate_cny':round(sum(r['charged'] or 0 for r in rows),6),
            'outstanding_reservation_cny':round(sum(r['reserved'] for r in rows if r['charged'] is None),6),
            'usage_unknown_or_reserved':sum(r['state']!='settled' for r in rows)}
with closing(sqlite3.connect(ledger.resolve().as_uri()+'?mode=ro',uri=True)) as db:
    db.row_factory=sqlite3.Row;db.execute('pragma query_only=on')
    for identity in manifest['jobs']:
        root=Path('/opt/monitor/geo-content/runtime/runs')/identity
        ids=[]
        for path in (root/'api/runs').glob('*/call/api_state.json'):
            value=json.loads(path.read_text())
            if value.get('reservation'):ids.append(value['reservation'])
        rows=[dict(row) for row in db.execute('select state,reserved,charged,created from costs where id in ('+','.join('?' for _ in ids)+')',ids)] if ids else []
        report['jobs'].append({'job_id':identity,'batch_total':summarize(rows),
                               'window_new_calls':summarize([r for r in rows if r['created']>=manifest['started_at']])})
target=base/'maintenance/20261015-unified/creation-cost-audit.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
public=Path('/tmp/geo-unified-export-20261015/creation-cost-audit.json');public.write_text(json.dumps(report,ensure_ascii=False,indent=2));public.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))

import json
import sqlite3
from pathlib import Path

shared = Path('/home/user/geo-editorial/runtime-api')
print('settings', (shared / 'settings.json').read_text())
with sqlite3.connect((shared / 'api/costs.sqlite').as_uri() + '?mode=ro', uri=True) as db:
    print('recent_daily_costs', db.execute('select date,sum(coalesce(charged,reserved)) from costs group by date order by date desc limit 2').fetchall())
    print('unknown_requests', db.execute('select count(*),sum(reserved) from costs where charged is null').fetchone())
    print('scopes', db.execute('pragma table_info(studio_cost_scopes)').fetchall())
base = Path('/opt/monitor/geo-content/runtime')
read = lambda p: json.loads(p.read_text()) if p.exists() else {}
for path in (base / 'runs').glob('*/job.json'):
    root = path.parent
    active = read(root / 'api/active.json')
    if active.get('state') in {'REQUESTING','AUTHORIZING','RESPONDED'}:
        print('active', root.name, active.get('state'))
job = read(base / 'runs/creation-1792575159-0a8f9221/job.json')
print('original_identity', {k:job.get(k) for k in ('job_id','studio_plan_id','date','budget_limits')})

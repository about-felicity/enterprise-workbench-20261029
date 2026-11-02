import subprocess, json,sqlite3
from pathlib import Path
for n in (3,4):
 r=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-strict')
 h=json.loads((r/'bridge_health.json').read_text());print(n,h['status'],h.get('progress'),h['geo_processed'],h['captured'],h['delivery_errors'])
 with sqlite3.connect(r/'tasks.sqlite') as db:print(db.execute('select event, detail from events order by id desc limit 4').fetchall())
 for p in (r/'receipts').glob('*.json'):
  v=json.loads(p.read_text());print('receipt',v['source_device'],v['save']['run_id'],v['analysis']['answer_length'],v['analysis']['source_count'])
print('memory',Path('/proc/meminfo').read_text().splitlines()[2])

"""Prove the old bridge reused yesterday's envelope for today's captures."""
import json
from pathlib import Path
import sys
sys.path.insert(0,'/opt/monitor/geo-capture')
from capture_bridge import read_rows,full_result
base=Path('/opt/monitor/geo-capture')
batch='geo-panel-baidu-ai-20261015-181822-d44632b8'
root=base/'batches'/batch
groups={}
for row in read_rows(root/'collector/tasks.sqlite',batch):
    if row['state']!='completed':continue
    value=json.loads(row['result'])
    if not value.get('captured_at','').startswith('2026-10-16') or not full_result(value):continue
    obs=json.loads((root/'observations'/(row['task_id']+'.json')).read_text())
    item=json.loads((root/'outbox'/(obs['request_id']+'.json')).read_text())
    target=item['record']['finished_at']
    group=groups.setdefault(row['question'],{'full_raw_today':0,'old_envelope_yesterday':0,'old_request_ids':set()})
    group['full_raw_today']+=1
    group['old_envelope_yesterday']+=int(target.startswith('2026-10-15'))
    group['old_request_ids'].add(obs['request_id'])
report={'questions':{q:{**g,'old_request_ids':sorted(g['old_request_ids'])} for q,g in groups.items()},
        'today_observations_reused_yesterday':sum(g['old_envelope_yesterday'] for g in groups.values())}
(base/'maintenance/20261016-daily-observations/cross-day-proof.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

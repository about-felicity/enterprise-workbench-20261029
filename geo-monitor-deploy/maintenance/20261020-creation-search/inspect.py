import json
from pathlib import Path
root=Path('/opt/monitor/geo-content/studio')
for file in sorted((root/'plans').glob('plan-*.json')):
 p=json.loads(file.read_text())
 print(json.dumps({k:p.get(k) for k in ('plan_id','name','enabled','legacy_capture','task_type','capture_time','channels','questions')},ensure_ascii=False))
 print('capture health', (root/'capture'/p['plan_id']/'health.json').read_text() if (root/'capture'/p['plan_id']/'health.json').exists() else 'not started')

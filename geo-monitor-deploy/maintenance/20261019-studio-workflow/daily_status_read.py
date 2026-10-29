import json
from pathlib import Path
r=Path('/opt/monitor/geo-capture')
for rel in ['daily_control_health.json','daily/2026-10-19/status.json']:
 d=json.loads((r/rel).read_text())
 print(rel,json.dumps(d,ensure_ascii=False)[:16000])

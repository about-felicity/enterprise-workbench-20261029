import json
from pathlib import Path
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1793063678-424352dc/api/runs/ad68a0d4aa82b81b4fd3dc3c')
for p in r.rglob('answer.json'):
 a=json.loads(p.read_text());print(str(p.relative_to(r)),a.get('finish_reason'),a.get('content','')[:2200])

import json
from pathlib import Path
p=Path('/opt/monitor/geo-content/runtime/runs/creation-1793057255-8a64b316/private_source_analysis/articles.jsonl')
for l in p.read_text().splitlines()[:3]:
 r=json.loads(l);print(json.dumps({k:v for k,v in r.items() if k not in ['text','html','body']},ensure_ascii=False)[:2400])

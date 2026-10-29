import json
from pathlib import Path
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13')
p=next((r/'days/2026-10-21/jobs').glob('*/02/research/research_input.json'));d=json.loads(p.read_text());b=d['reference_design']
print(json.dumps(b['products'][0],ensure_ascii=False))
k=json.loads((p.parent/'research_result.json').read_text());print(json.dumps(k.get('knowledge_units',[])[:3],ensure_ascii=False))
print('SOURCES')
s=json.loads((r/'days/2026-10-21/media_articles.json').read_text());print(len(s));print(type(s));print(s[0].keys())

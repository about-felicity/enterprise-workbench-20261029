import json
from pathlib import Path
root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792475798-478ca528/days/2026-10-20')
sources=json.loads((root/'media_articles.json').read_text())
if isinstance(sources,dict):sources=sources.get('articles',sources.get('sources',[]))
for s in sources[:3]:
 print(json.dumps({'url':s.get('url'),'title':s.get('article',{}).get('title'),'text':s.get('article',{}).get('text','')[:2400],'headings':s.get('article',{}).get('headings')},ensure_ascii=False))

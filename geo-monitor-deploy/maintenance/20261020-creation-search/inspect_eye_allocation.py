import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content/engine']
from geo_source_cards.genre_pools import classify_source
root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792479954-8a96bc88/days/2026-10-20')
sources={s['url']:s for s in json.loads((root/'media_articles.json').read_text())}
allocation=json.loads((root/'article_allocation.json').read_text());out=[]
for category,urls in allocation['selected'].items():
 for url in urls:
  source=sources[url];article=source['article'];classification=classify_source(source)
  out.append({'category':category,'title':article['title'],'chars':len(article['text']),'products':len(classification['products']),'classification':classification['status'],'preview':article['text'][:1100] if category=='科普类' else article['text'][:180]})
Path('/tmp/eye-allocation-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))

import json,sys
from pathlib import Path
B=Path(__file__).resolve().parent;s=json.loads((B/'state.json').read_text());root=Path(s['capture_root'])/'days'/s['date']
sys.path[:0]=[str(B/'engine'),str(B)]
from geo_source_cards.daily_editorial import DEFAULT_MEDIA,media_identity
seen={}
for f in root.glob('*/results.jsonl'):
 for line in f.read_text().splitlines():
  r=json.loads(line)
  for v in r.get('sources',[]):
   seen[v['url']]={'title':v.get('title'),'url':v['url'],'question':r['question'],'model':r['model']}
allowed=[v for v in seen.values() if media_identity(v['url'],DEFAULT_MEDIA)]
print(json.dumps({'unique_sources':len(seen),'eligible_media_links':len(allowed),'sample':allowed[:20]},ensure_ascii=False,indent=2))

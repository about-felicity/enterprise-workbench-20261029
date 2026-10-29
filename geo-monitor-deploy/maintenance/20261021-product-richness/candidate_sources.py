import json,sys
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture/maintenance/20261021-product-richness/stage/engine')
from geo_source_cards.genre_pools import classify_source
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13')
s=json.loads((r/'days/2026-10-21/media_articles.json').read_text());used={json.loads(p.read_text()).get('reference_design',{}).get('primary_url') for p in (r/'days/2026-10-21/jobs').glob('*/*/research/research_input.json')}
for v in s:
 a=classify_source(v)
 if a['genre']=='排行类' and a['status']=='ready' and v['url'] not in used:print(json.dumps({'url':v['url'],'title':a['title'],'products':[p['name'] for p in a['products']]},ensure_ascii=False))

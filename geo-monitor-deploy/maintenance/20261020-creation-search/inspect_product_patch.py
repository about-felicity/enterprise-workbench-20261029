import json,sys
from pathlib import Path
from geo_source_cards.genre_pools import classify
from geo_source_cards.reference_design import product_blocks
for jid in ['creation-1792475798-478ca528','creation-1792475798-7d2fc250']:
 root=Path('/opt/monitor/geo-content/runtime/runs')/jid
 sources=json.loads((root/'days/2026-10-20/media_articles.json').read_text())
 result=classify(sources,1)
 print(json.dumps({'job':jid,'pools':[{ 'label':c['label'],'eligible':sum(s['eligible'] for s in c['sources'])} for c in result['categories']],'first_roster':[p['name'] for p in product_blocks(sources[0]['article'])]},ensure_ascii=False))
 for file in (root/'approved').glob('*/*/*/draft.md'):
  body=file.read_text();print(json.dumps({'approved':str(file),'contains_old_brand':'科熙本' in body,'contains_current_product':'焕颜计' in body,'chars':len(body)},ensure_ascii=False))

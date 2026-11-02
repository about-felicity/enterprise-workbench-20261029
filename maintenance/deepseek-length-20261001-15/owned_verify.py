import json,collections,csv
from pathlib import Path
D=Path('maintenance/deepseek-length-20261001-15');d=json.loads((D/'owned_dataset.json').read_text('utf8'));strict={r['canonical_url']:r for r in csv.DictReader((D/'DeepSeek文章样本明细.csv').open(encoding='utf-8-sig'))};counts=collections.defaultdict(lambda:[0,0])
for a in d['articles']:
 if not a.get('own_products'):continue
 n=sum(e['source_complete'] is True for e in a['events'])
 if not n:continue
 label='title' if a['title_products'] else 'body_only';counts[label][0]+=1;counts[label][1]+=n
 if a['canonical_url'] not in strict:print('OUTSIDE_ARTICLE_SAMPLE',a['title'][:65],a['status'],a.get('quality'),n)
print(dict(counts))
for a in sorted(d['articles'],key=lambda a:len(a['events']),reverse=True):
 if a.get('own_products') and a['canonical_url'] in strict:
  print('TOP',json.dumps({'url':a['url'],'title':a.get('article_title') or a['title'],'products':a['own_products'],'title_products':a['title_products'],'refs':sum(e['source_complete'] is True for e in a['events']),'evidence':a.get('product_evidence')},ensure_ascii=False))
  if len([x for x in []])>5:break

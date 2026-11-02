import json,csv,collections
from pathlib import Path
D=Path('maintenance/deepseek-length-20261001-15');d=json.loads((D/'owned_dataset.json').read_text('utf8'));owned={a['canonical_url']:a for a in d['articles'] if a.get('own_products')};labels=json.loads((D/'domain_classification.json').read_text('utf8'))
from urllib.parse import urlsplit
strict={r['canonical_url']:r for r in csv.DictReader((D/'DeepSeek文章样本明细.csv').open(encoding='utf-8-sig'))}
for scope,rs in [('all_regions',[a for a in owned.values()]),('nonforeign',[a for a in owned.values() if labels[urlsplit(a['canonical_url']).netloc]['region'] in {'mainland','hk_macao_taiwan'}]),('strict_article',[a for k,a in owned.items() if k in strict])]:
 rr=[(a,[e for e in a['events'] if e['source_complete'] is True]) for a in rs];rr=[(a,es) for a,es in rr if es]
 print(scope,'URLS',len(rr),'CITATIONS',sum(len(es) for a,es in rr),'ANSWERS',len({(e['day'],e['question']) for a,es in rr for e in es}))
 by=collections.defaultdict(lambda:{'urls':set(),'refs':0})
 for a,es in rr:
  for product in a['own_products']:by[product]['urls'].add(a['canonical_url']);by[product]['refs']+=len(es)
 print(json.dumps({k:{'urls':len(v['urls']),'refs':v['refs']} for k,v in sorted(by.items(),key=lambda x:x[1]['refs'],reverse=True)},ensure_ascii=False))
print('UNVERIFIABLE_DB_OWN',sum(any(a.get('db_own_brand_flags',[])) and not a.get('own_products') for a in d['articles']))

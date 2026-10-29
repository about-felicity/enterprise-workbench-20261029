import json,sys,difflib
from pathlib import Path
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from geo_source_cards.rewrite_v2.material_manager import raw_material
root=B/'runtime/runs'/json.loads((B/'state.json').read_text())['job_id'];product=json.loads((root/'product.json').read_text());raw=raw_material(product)
for p in root.glob('api/runs/*/material-call/response.json'):
 value=json.loads(p.read_text());print('response',p)
 for k,items in value.items():
  if not isinstance(items,list):continue
  for quote in items:
   if quote not in raw and json.dumps(quote,ensure_ascii=False)[1:-1] not in raw:
    print(json.dumps({'layer':k,'quote':quote,'closest':difflib.get_close_matches(quote,product['raw_source_text'].splitlines(),n=2,cutoff=.3)},ensure_ascii=False))

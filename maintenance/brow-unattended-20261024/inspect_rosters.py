import sys,json
from pathlib import Path
B=Path(__file__).resolve().parent;sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from creation import runtime
from geo_source_cards.reference_design import product_blocks
r=B/'runtime/runs'/runtime.read(B/'state.json')['job_id']
for p in r.glob('days/*/jobs/*/*/writer/rewrite_context.json'):
 c=runtime.read(p);blocks=product_blocks(c['reference'])
 print(json.dumps({'article':str(p.parent.parent.relative_to(r)),'products':[{'name':b['name'],'chars':len(b['excerpt']),'start':b['excerpt'][:100]} for b in blocks]},ensure_ascii=False))

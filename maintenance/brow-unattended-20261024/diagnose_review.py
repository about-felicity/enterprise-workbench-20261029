import json,os,sys
from pathlib import Path
B=Path(__file__).resolve().parent;os.environ['GEO_CREATION_ROOT']=str(B/'runtime');sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from creation import runtime
from geo_source_cards.rewrite_v2.common import prompt_material
root=runtime.job_root(runtime.read(B/'state.json')['job_id']);budget=runtime.SharedBudget(root)
for folder in sorted((root/'days').glob('*/jobs/*/*')):
 c=runtime.read(folder/'writer/rewrite_context.json');m=runtime.read(folder/'writer/rewrite_material.json');r=runtime.read(folder/'review/result.json')
 print(json.dumps({'article':str(folder.relative_to(root)), 'product_keys':list(c['product']),
  'source_chars':len(c['product'].get('raw_source_text','')),'prompt_material_chars':len(json.dumps(prompt_material(m),ensure_ascii=False)),
  'remaining':budget.remaining({'date':runtime.read(B/'state.json')['date'],'category':c['category']['label'],'number':c['category']['number'],'cost_scope':'article'},'review'),
  'pass':r.get('pass'),'findings':r.get('evidence_report',{}).get('findings',[]),
  'dismissed':r.get('dismissed_findings',[])},ensure_ascii=False))
budget.db.close()

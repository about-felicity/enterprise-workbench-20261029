"""Deterministic checks of old text; not a new article acceptance."""
import json,sys
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated';sys.path[:0]=[str(S/'engine'),str(S)]
from geo_source_cards import quality_checks as q,reference_design as ref
from geo_source_cards.genre_length import hanzi,body
from geo_source_cards.repair_router import route
read=lambda p:json.loads(Path(p).read_text('utf8'))
result=[]
for s in read(D/'replay-results.json')['samples']:
 w=Path(s['work_dir'])/'writer';cost=w.parent/'cost-only';text=(cost/'draft.md').read_text('utf8');k,p=read(w/'knowledge.json'),read(w/'product.json')
 c=read(w/'compilation.json');a=read(S/'evidence/api/runs'/s['run_id']/'article_structure.json')
 required='\n'.join('\n'.join(v['structure_task']['required_content']) for v in c['sections'])
 leaked=[v for part in a['sections'] for v in part['required_content'] if len(v)>7 and '只使用当前任务' not in v and v in required]
 assert not leaked
 findings=q.findings(text,k,p);errors=ref.validate_structure(text,k['reference_design'])
 exhausted=route(text,k,p,{},reason='离线边界核对',attempts=2,feasibility=c['feasibility'])
 assert exhausted['action']=='REPAIR_EXHAUSTED'
 result.append({'sample':s['category']+str(s['number']).zfill(2),'historical_chars':len(text),'historical_body_hanzi':hanzi(body(text)),'exceeds_max_6000':len(text)>6000,
 'expected_product_count_including_owned':len(ref.clean_roster(k['reference_design'])['products'])+1,
 'deterministic_findings':findings,'historical_structure_errors':errors,'original_specific_required_content_leaks':leaked,
 'two_repairs_exhausted_action':exhausted['action'],'not_a_new_draft':True})
assert any(v['kind']=='contradiction' and '实际11款' in v['reason'] for v in result[1]['deterministic_findings'])
(D/'saved-text-checks.json').write_text(json.dumps({'zero_api_replay':True,'new_api_calls':0,'samples':result},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(result,ensure_ascii=False,indent=2))

import sys,json,time
from pathlib import Path
S=Path('/opt/monitor/geo-capture/maintenance/20261022-article-quality/stage')
sys.path[:0]=[str(S),str(S/'engine'),'/opt/monitor/geo-content']
from creation.runtime import SharedBudget,read
from geo_source_cards.article_compiler import compile_article
from geo_source_cards.consumer_prompts import evidence_units
from geo_source_cards.section_writer import plan
from geo_source_cards.genre_length import policy
from geo_source_cards.api_budget import OUTPUT
D=S.parent;root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792575159-0a8f9221');budget=SharedBudget(root);out=[]
for parent in (root/'days/2026-10-21/compiler-pilots').glob('*/*'):
 writer=parent/'writer';k,p=read(writer/'knowledge.json'),read(writer/'product.json');contract=compile_article(k,p,evidence_units(writer))
 tickets=[read(t) for t in (root/'queue').glob('*/ticket.json') if read(t).get('location')==str(writer.relative_to(root)) and read(t).get('meta',{}).get('compiler_pilot_release')=='practical-v1']
 assert tickets,writer
 meta=tickets[-1]['meta'];available=budget.remaining(meta,'writer');tasks=plan(contract,policy(k.get('reference_design')) or {'min_body_hanzi':1400,'min_lead_hanzi':180})
 writer_output=sum(min(2600,max(900,t['target_hanzi']*3+350)) for t in tasks)
 # Output reservations alone already exceed the original article remainder.
 # Input reservations, retry attempts and two repair rounds are deliberately
 # excluded: this is a lower bound on the complete initial preflight reserve.
 tokens=2400+writer_output+1800+1600
 minimum=tokens*OUTPUT/1000000
 out.append({'category':meta['category'],'number':meta['number'],'remaining_cny':available,'initial_output_reservation_lower_bound_cny':minimum,'input_and_repair_cost_not_included':True,'planned_initial_calls':len(tasks)+3,'allowed_to_start':available>=minimum,'actual_generation_calls':0,'actual_review_calls':0,'actual_repair_calls':0})
budget.close();assert len(out)==2 and all(not v['allowed_to_start'] for v in out)
value={'at':time.time(),'samples':out,'actual_new_calls':0,'actual_new_cost_cny':0,'real_end_to_end_acceptance':'not_started_budget_insufficient','limits_changed':False}
(D/'budget-preflight.json').write_text(json.dumps(value,ensure_ascii=False,indent=2));print(json.dumps(value,ensure_ascii=False))

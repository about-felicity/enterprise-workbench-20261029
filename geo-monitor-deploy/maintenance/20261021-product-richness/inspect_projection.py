import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards.consumer_prompts import reader_knowledge
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13/days/2026-10-21/jobs/排行类/04-projection-repair')
k=json.loads((r/'writer/knowledge.json').read_text());research=json.loads((r/'research/research_result.json').read_text());units,outline,proj=reader_knowledge(k,json.loads((r/'writer/product.json').read_text()),research['knowledge_units'])
print(json.dumps({'missing':proj['products_without_neutral_details'],'changes':proj['changes']},ensure_ascii=False))
print(json.dumps([u for u in research['knowledge_units'] if any(e.get('quote_id','').startswith(('R2_','R3_','R4_')) for e in u.get('evidence',[]))],ensure_ascii=False)[:6500])
b=json.loads((r/'research/research_input.json').read_text())['reference_design']
for p in b['products'][1:4]:print(json.dumps(p,ensure_ascii=False)[:1800])

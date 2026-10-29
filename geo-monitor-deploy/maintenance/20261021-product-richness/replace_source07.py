import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards import daily_editorial as d
from geo_source_cards.genre_pools import classify_source
from geo_source_cards.genre_outline import captured_neutral_details
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards.reference_design import design
from geo_source_cards.product_identity import bind as bind_product
from geo_source_cards.source_contract import bind as bind_source
from geo_source_cards.staged_editorial import prepare
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13');m=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');mark=m/'replace-source07.json';assert not mark.exists()
day=r/'days/2026-10-21';sources=d.read(day/'media_articles.json');used={d.read(p).get('reference_design',{}).get('primary_url') for p in (day/'jobs').glob('*/*/research/research_input.json')}
candidates=[]
for s in sources:
 a=classify_source(s)
 if s['url'] in used or a['genre']!='排行类' or a['status']!='ready' or a['audience']=='children':continue
 spans={f'R{i}_1':{'quote':p['excerpt']} for i,p in enumerate(a['products'],1)}
 recovered=captured_neutral_details({'units':[]},{'genre':'ranking','products':a['products']},spans)['units']
 prefixes={e.split('_')[0] for u in recovered for e in u['evidence']}
 if all('R'+str(i) in prefixes for i in range(1,len(a['products'])+1)):
  candidates.append((len(a['products']),s))
assert candidates,'No suitable same-day reference'
_,s=min(candidates,key=lambda v:v[0]);url=s['url']
loc=day/'jobs/排行类/07-source-replacement';assert not loc.exists();loc.mkdir()
blue=bind_source(bind_product(design([s],'排行类'),d.read(day/'product.json')),[s],'2026-10-21')
records=[{'model':'daily_media','question':'保湿面膜选购','body':'多产品逐款介绍','sources':[s]}];atomic_write(loc/'articles.jsonl',''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in records))
prepare(loc/'research',loc/'articles.jsonl',day/'product.json',reference_design=blue)
cat=d.read(day/'jobs/排行类/07/category.json');atomic_json(loc/'category.json',{**cat,'angle':s['article']['title'],'source_urls':[url],'replaces_source':d.read(day/'jobs/排行类/07/research/research_input.json')['reference_design']['primary_url']})
new=d.publish_ticket(r,'research',loc/'research',['research_input.json','research_task.txt'],['research_result.json'],{'date':'2026-10-21','category':'排行类','number':7,'source_replacement':1})
with process_lock(r/'coordinator.lock',blocking=True):
 for p in (r/'queue').glob('*/ticket.json'):
  v=d.read(p)
  if v['stage']!='writer' or v['meta'].get('category')!='排行类' or v['meta'].get('number')!=7:continue
  assert v['state'] in ['needs_attention','revision_requested']
  if v['state']=='needs_attention':assert 'research_material_insufficient' in v['error']
  atomic_json(p,{**v,'previous_state':v['state'],'state':'revision_requested','replaced_by':new,'resolution':'same_day_source_lacks_neutral_details_replaced'})
 plan=d.read(day/'category_plan.json')
 for v in plan['planned']:
  if v['category']=='排行类' and v['number']==7:v['replaces_ticket']=v['ticket'];v['ticket']=new
 atomic_json(day/'category_plan.json',plan)
mark.write_text(json.dumps({'at':time.time(),'new_ticket':new,'selected_url':url,'new_source_product_count':len(blue['products']),'candidate_count':len(candidates),'original_budget_preserved':True},ensure_ascii=False,indent=2));print(mark.read_text())

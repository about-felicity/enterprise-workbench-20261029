import json,sys,time,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from geo_source_cards import daily_editorial as d
from geo_source_cards.genre_pools import classify_source
from geo_source_cards.genre_outline import captured_neutral_details
from geo_source_cards.genre_prompts import quote_chunks
from geo_source_cards.consumer_prompts import reader_knowledge
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards.reference_design import design
from geo_source_cards.product_identity import bind as bind_product
from geo_source_cards.source_contract import bind as bind_source
from geo_source_cards.staged_editorial import prepare
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13');m=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');mark=m/'replace-source234.json';assert not mark.exists()
day=r/'days/2026-10-21';sources=d.read(day/'media_articles.json');product=d.read(day/'product.json')
used={d.read(p).get('reference_design',{}).get('primary_url') for p in (day/'jobs').glob('*/*/research/research_input.json')}
textkey=lambda s:hashlib.sha256(''.join(s['article']['text'].split()).encode()).hexdigest()
used_hash={textkey(s) for s in sources if s['url'] in used};candidates=[]
for s in sources:
 a=classify_source(s)
 if s['url'] in used or textkey(s) in used_hash or a['genre']!='排行类' or a['status']!='ready' or a['audience']=='children':continue
 blue=bind_product(design([s],'排行类'),product);spans={}
 for i,p in enumerate(blue['products'],1):
  for j,q in quote_chunks(p['excerpt'],s['article']['text']):spans[f'R{i}_{j}']={'quote':q,'url':s['url']}
 units=captured_neutral_details({'units':[]},blue,spans)['units']
 ku=[{'id':u['id'],'type':'source_claim','content':u['text'],'verification':'not_independently_verified','evidence':[{'quote_id':e,**spans[e]} for e in u['evidence']]} for u in units]
 _,_,projection=reader_knowledge({'knowledge_units':ku,'reference_design':blue,'outline':{}},product,ku)
 if not projection['products_without_neutral_details']:candidates.append((len(blue['products']),s,blue,textkey(s)))
replacements={};chosenhash=set()
for number in [2,3,4]:
 choices=[v for v in candidates if v[3] not in chosenhash];assert choices,'No adequate independent sources left'
 _,s,blue,h=min(choices,key=lambda v:v[0]);chosenhash.add(h);url=s['url'];blue=bind_source(blue,[s],'2026-10-21')
 loc=day/f'jobs/排行类/{number:02d}-source-replacement';assert not loc.exists();loc.mkdir()
 records=[{'model':'daily_media','question':'保湿面膜选购','body':'多产品逐款介绍','sources':[s]}];atomic_write(loc/'articles.jsonl',''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in records));prepare(loc/'research',loc/'articles.jsonl',day/'product.json',reference_design=blue)
 cat=d.read(day/f'jobs/排行类/{number:02d}/category.json');atomic_json(loc/'category.json',{**cat,'angle':s['article']['title'],'source_urls':[url],'replaces_source':d.read(day/f'jobs/排行类/{number:02d}/research/research_input.json')['reference_design']['primary_url']})
 new=d.publish_ticket(r,'research',loc/'research',['research_input.json','research_task.txt'],['research_result.json'],{'date':'2026-10-21','category':'排行类','number':number,'source_replacement':1});replacements[number]={'ticket':new,'url':url,'products':len(blue['products'])}
 with process_lock(r/'coordinator.lock',blocking=True):
  for p in (r/'queue').glob('*/ticket.json'):
   v=d.read(p)
   if v['id']==new or v['meta'].get('category')!='排行类' or v['meta'].get('number')!=number:continue
   assert v['state']!='claimed','An existing request must finish before replacement'
   if v['state'] in ['pending','needs_attention']:
    assert v['stage'] in ['research','writer'];atomic_json(p,{**v,'previous_state':v['state'],'state':'revision_requested','replaced_by':new,'resolution':'source_replaced_after_preflight_or_research_handoff_failure'})
 plan=d.read(day/'category_plan.json')
 for v in plan['planned']:
  if v['category']=='排行类' and v['number']==number:v['replaces_ticket']=v['ticket'];v['ticket']=new
 atomic_json(day/'category_plan.json',plan)
allocation=d.read(day/'article_allocation.json')
for number,v in replacements.items():
 old=allocation['selected']['排行类'][number-1];allocation['selected']['排行类'][number-1]=v['url'];allocation.setdefault('source_replacements',[]).append({'before':old,'after':v['url'],'reason':'中性资料不足，实际逐字引文投影仍不可用，换同日不同原文'})
seven=d.read(m/'replace-source07.json');allocation['selected']['排行类'][6]=seven['selected_url'];atomic_json(day/'article_allocation.json',allocation)
mark.write_text(json.dumps({'at':time.time(),'replacements':replacements,'qualifying_candidates':len(candidates),'original_budget_preserved':True,'same_day_frozen_sources_only':True},ensure_ascii=False,indent=2));print(mark.read_text())

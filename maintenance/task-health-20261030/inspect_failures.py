import json,sys,collections
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,owned_sources,materials
from geo_source_cards.source_scope import anchors,evaluate
for identity in ['creation-1793316451-c7f2aa76','creation-1793316449-e75f0dab','creation-1793316447-0b6c816c','creation-1793312939-21db143b','creation-1793312937-1080b026','creation-1793312933-96081eb7']:
 root=runtime.job_root(identity);job=runtime.read(root/'job.json');paths=list(root.glob('private_source_analysis*/articles.jsonl'))
 if not paths:continue
 p=max(paths,key=lambda p:p.stat().st_mtime);rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
 terms=anchors([job['question']],runtime.read(root/'product.json'));seen=set();counts=collections.Counter();examples=[];errors=[]
 for row in rows:
  for s in row['sources']:
   if s['url'] in seen:continue
   seen.add(s['url']);a=s.get('article',{});scope=evaluate(s,terms);owned=owned_sources.ownership(s)
   if owned['owned']:kind='owned'
   elif scope['status']=='off_topic':kind='off_topic'
   else:kind=a.get('status','missing')
   counts[kind]+=1
   if a.get('status')=='failed' and len(errors)<2:errors.append({'url':s['url'],'attempts':a.get('attempts')})
   if a.get('status')=='fetched' and scope['status']=='ready' and len(examples)<2:examples.append({'title':a.get('title'),'owned':owned})
 print(json.dumps({'id':identity,'question':job['question'],'analysis':p.parent.name,'unique_reasons':counts,'read_errors':errors,'relevant_examples':examples},ensure_ascii=False),flush=True)

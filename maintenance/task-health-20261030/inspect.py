import json,collections,sqlite3,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
from geo_source_cards.source_scope import anchors,evaluate
ids=['creation-1793321691-cba78663','creation-1793316451-c7f2aa76','creation-1793316449-e75f0dab','creation-1793316447-0b6c816c','creation-1793312939-21db143b','creation-1793312937-1080b026','creation-1793312933-96081eb7']
for identity in ids:
 root=runtime.job_root(identity);job=runtime.read(root/'job.json');terms=anchors([job['question']],runtime.read(root/'product.json'))
 print('JOB',json.dumps({'id':identity,'question':job['question'],'anchors':terms,'preparation':job.get('preparation'),'attempt':job.get('supplement_attempt'),'http_failure':recovery.http_failure(root)},ensure_ascii=False))
 paths=list(root.glob('private_source_analysis*/articles.jsonl'))
 if not paths:continue
 p=max(paths,key=lambda p:p.stat().st_mtime);rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()]
 sources=[s for r in rows for s in r.get('sources',[])];counts=collections.Counter(s.get('article',{}).get('status') for s in sources)
 print('ANALYSIS',p.name,p.parent.name,json.dumps(counts),'records',len(sources),'unique',len({s['url'] for s in sources}))
 selected=collections.Counter()
 for s in sources:
  a=s.get('article',{});status=a.get('status');scope=evaluate(s,terms);key=(status,scope['status'])
  if selected[key]>=3:continue
  selected[key]+=1
  print('SOURCE',json.dumps({'url':s['url'],'title':s.get('title'),'article_title':a.get('title'),'status':status,'reason':a.get('reason') or a.get('error'),'final_url':a.get('final_url'),'text_length':len(a.get('text','')),'scope':scope,'snippet':a.get('text','')[:180]},ensure_ascii=False))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 for plan in ['plan-f0d530e5eae24fb981e4b191dffeb0ed','plan-4c988f3863344f52aff3aa2b1f96beb2','plan-47fbabcdee8c4807a4f895016f830dbc']:
  used=db.execute('select coalesce(sum(coalesce(c.charged,c.reserved)),0) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=? and s.task_day=?',(plan,'2026-10-30')).fetchone()[0]
  print('BUDGET',plan,used)

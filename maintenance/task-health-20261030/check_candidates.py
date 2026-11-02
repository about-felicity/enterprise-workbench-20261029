import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,owned_sources
from geo_source_cards.article_fetch import ScraplingArticleFetcher
for identity in ['creation-1793316451-c7f2aa76','creation-1793316449-e75f0dab','creation-1793316447-0b6c816c']:
 root=runtime.job_root(identity);paths=list(root.glob('private_source_analysis*/articles.jsonl'));p=max(paths,key=lambda p:p.stat().st_mtime)
 rows=[json.loads(x) for x in p.read_text().splitlines() if x.strip()];seen=set();examples=[]
 for row in rows:
  for s in row['sources']:
   a=s.get('article',{});url=s['url']
   if url in seen or a.get('status')!='fetched' or owned_sources.ownership(s)['owned']:continue
   seen.add(url);title=a.get('title') or s.get('title','')
   if any(term in title+a.get('text','')[:1000] for term in ['定型喷雾','定型发胶','发胶喷雾','造型喷雾']):examples.append({'url':url,'title':title,'snippet':a.get('text','')[:160]})
 print('CANDIDATES',identity,json.dumps(examples[:5],ensure_ascii=False),flush=True)
url='https://baijiahao.baidu.com/s?id=1879442581254540709&wfr=spider&for=pc'
t=time.monotonic();a=ScraplingArticleFetcher(backends=('http',),timeout=15)(url)
print('CURRENT_FETCH',json.dumps({'seconds':round(time.monotonic()-t,2),'status':a.get('status'),'title':a.get('title'),'length':len(a.get('text','')),'attempts':a.get('attempts')},ensure_ascii=False),flush=True)

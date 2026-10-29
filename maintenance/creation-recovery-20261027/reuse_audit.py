import sys,json,collections
from pathlib import Path
from urllib.parse import urlsplit,parse_qsl,urlencode,urlunsplit
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,materials
from geo_source_cards.article_quality import normalize

def key(url):
 u=urlsplit(url);q=parse_qsl(u.query,keep_blank_values=True)
 if u.hostname=='baijiahao.baidu.com' and u.path=='/s' and dict(q).get('id'):q=[('id',dict(q)['id'])]
 return urlunsplit((u.scheme,u.netloc,u.path,urlencode(sorted(q)),''))
index={}
for path in (runtime.BASE/'runs').glob('*/private_source_analysis/articles.jsonl'):
 for row in materials.read_lines(path):
  for s in row.get('sources',[]):
   a=normalize(s.get('article',{}))
   if a.get('status')=='fetched':index[key(s['url'])]={'article':a,'source_file':str(path)}
results=[]
for root in (runtime.BASE/'runs').iterdir():
 j=runtime.read(root/'job.json')
 if j.get('date','')<'2026-10-26' or j.get('preparation')!='insufficient' or runtime.read(root/'control.json').get('reason')=='plan_deleted':continue
 path=root/'private_source_analysis/articles.jsonl'
 if not path.exists():continue
 rows=materials.read_lines(path);matched=0
 for row in rows:
  for s in row.get('sources',[]):
   if normalize(s.get('article',{})).get('status')!='fetched' and key(s['url']) in index:matched+=1
 results.append({'job':root.name,'question':j.get('question'),'reuse_candidates':matched})
print(json.dumps({'saved_sources':len(index),'jobs':results},ensure_ascii=False))

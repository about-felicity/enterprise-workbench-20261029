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

from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards.daily_editorial import prepare_day
from geo_source_cards.article_fetch import check_article_relevance
import shutil,time
base=Path('/opt/monitor/geo-content/maintenance/recovery-20261027/source-reuse');base.mkdir(exist_ok=True)
results=[]
for root in (runtime.BASE/'runs').iterdir():
 j=runtime.read(root/'job.json')
 if j.get('date','')<'2026-10-26' or j.get('preparation')!='insufficient' or runtime.read(root/'control.json').get('reason')=='plan_deleted':continue
 path=root/'private_source_analysis/articles.jsonl'
 if not path.exists():continue
 rows=materials.read_lines(path);matches=[]
 for row in rows:
  for s in row.get('sources',[]):
   if normalize(s.get('article',{})).get('status')!='fetched' and key(s['url']) in index:
    saved=index[key(s['url'])];article=check_article_relevance(saved['article'],s.get('title',''))
    if normalize(article).get('status')=='fetched':
     s['article']={**article,'reused_from_saved_source':saved['source_file']};matches.append({'url':s['url'],'source_file':saved['source_file']})
 filtered,count=materials.usable_source_rows(rows)
 if count<3:continue
 with process_lock(root/'api/worker.lock',blocking=False):
  if not (base/root.name).exists():shutil.copytree(root,base/root.name)
  atomic_write(path,''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
  atomic_write(root/'geo_articles.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in filtered))
  dayfile=root/'days'/j['date']/'day.json'
  assert not list((root/'queue').glob('*/ticket.json')) and not list((root/'approved').glob('*/*/*/receipt.json'))
  assert runtime.read(dayfile).get('status') in {'blocked_insufficient_sources','blocked_no_media_articles'}
  dayfile.unlink() # Original day is retained in the per-job recovery backup.
  prepared=prepare_day(root,root/'geo_articles.jsonl',root/'product.json',j['date'],max_per_category=j['max_per_category'])
  j.update(preparation='ready',prepared=prepared,material_counts={'full_articles':count,'private_observations':len(rows),'geo_observations':0});j.pop('material_shortfall',None)
  atomic_json(root/'job.json',j);atomic_json(root/'source_reuse_recovery.json',{'at':time.time(),'matches':matches,'no_network_requests':True})
  runtime.resume(root,check_balance=False)
  results.append({'job':root.name,'reused_sources':len(matches),'full_articles':count})
atomic_json(base/'result.json',results);print(json.dumps(results,ensure_ascii=False))

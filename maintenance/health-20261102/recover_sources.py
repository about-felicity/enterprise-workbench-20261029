import hashlib,json,shutil,sys,time
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,materials
from creation.source_cache import SourceCache
from geo_source_cards.runtime import atomic_json,process_lock
from creation.owned_sources import ownership
from geo_source_cards.source_scope import anchors,evaluate

audit=Path('/opt/monitor/geo-content/maintenance/recovery-20261102/source-cache');audit.mkdir(parents=True,exist_ok=True)
for p in sorted((runtime.BASE/'runs').glob('*/job.json')):
 job=runtime.read(p);root=p.parent
 if job.get('date')!='2026-11-01' or job.get('preparation')!='insufficient':continue
 try:
  with process_lock(root/'api/worker.lock',blocking=False):
   job=runtime.read(p);day=root/'days'/job['date']/'day.json'
   if job.get('preparation')!='insufficient' or list((root/'queue').glob('*/ticket.json')):continue
   rows=materials.read_lines(root/'private_observations.jsonl')
   cache=SourceCache(root,lambda u:None,content_db=runtime.CONTENT)
   terms=anchors([job['question']],runtime.read(root/'product.json'));usable=[]
   for row in rows:
    for source in row.get('sources',[]):
     key=hashlib.sha256(source['url'].encode()).hexdigest()+'.json'
     article=cache.shared_article(source['url']) or cache.valid(root/'source_read_cache'/key,source['url'])
     if not article or article.get('status')!='fetched':continue
     candidate={**source,'article':article}
     if not ownership(candidate)['owned'] and evaluate(candidate,terms)['status']!='off_topic':usable.append(source['url'])
   if not usable:print('NO_RECENT_CACHE',root.name,flush=True);continue
   backup=audit/root.name
   if (backup/'result.json').exists():print('ALREADY_RECOVERED',root.name,flush=True);continue
   backup.mkdir(exist_ok=True)
   if not (backup/'job.json').exists():shutil.copy2(p,backup/'job.json')
   if not (backup/'day.json').exists():shutil.copy2(day,backup/'day.json')
   folder=root/('private_source_analysis'+('-supplement-'+str(job['supplement_attempt']) if job.get('supplement_attempt') else ''))
   if folder.exists() and not (backup/'analysis').exists():shutil.copytree(folder,backup/'analysis')
   if not day.exists() and (backup/'day.json').exists():shutil.copy2(backup/'day.json',day)
   assert runtime.read(day).get('status') in ['blocked_insufficient_sources','blocked_no_media_articles']
   # Same fence as supplemental refresh: no queue or approved output exists.
   assert not list((root/'approved').rglob('receipt.json'))
   day.rename(backup/('displaced-day-'+str(time.time_ns())+'.json'))
   # The analysis layer has a second URL cache; archive its old failed fetches
   # so it can consult the newly available exact-URL shared snapshots.
   if folder.exists():folder.rename(backup/('displaced-analysis-'+str(time.time_ns())))
   class OfflineFetcher:
    def __call__(self,url):return {'status':'failed','requested_url':url,'error':'No recent verified cache; network fetch deferred during cache-only recovery','text':''}
   # All source policy/ownership/topic/quality gates in the normal preparation run.
   try:
    with patch('geo_source_cards.article_fetch.ScraplingArticleFetcher',OfflineFetcher):
     result=materials.prepare(root,job)
   except Exception:
    if not day.exists():shutil.copy2(backup/'day.json',day)
    raise
   runtime.resume(root,check_balance=False)
   report={'job':root.name,'question':job['question'],'cached_urls':sorted(set(usable)),'prepared':result.get('preparation'),'no_network_source_fetch':True,'budget_limits':job.get('budget_limits'),'at':time.time()}
   atomic_json(backup/'result.json',report);print('SOURCE_RECOVERED',json.dumps(report,ensure_ascii=False),flush=True)
 except RuntimeError as error:
  print('BUSY',root.name,str(error),flush=True)

import json,sys,sqlite3,hashlib,urllib.request
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.source_cache import SourceCache
base=Path('/opt/monitor/geo-content/maintenance/task-health-20261030')
release=json.loads((base/'release.json').read_text());assert all(hashlib.sha256(Path(f['server']).read_bytes()).hexdigest()==f['sha256'] for f in release['files'])
ids=['creation-1793316451-c7f2aa76','creation-1793316449-e75f0dab','creation-1793316447-0b6c816c','creation-1793312939-21db143b','creation-1793312937-1080b026','creation-1793312933-96081eb7']
for identity in ids:
 root=runtime.job_root(identity)
 # Check production cache reuse without a network request or changing task state.
 samples=list(root.glob('private_source_analysis*/article_cache/*.json'))
 hits=0
 def forbidden(url):raise RuntimeError('Network not allowed in cache verification')
 cache=SourceCache(root,forbidden)
 for p in samples[:100]:
  a=json.loads(p.read_text());u=a.get('requested_url')
  if u and cache.valid(p,u) and a.get('status')=='fetched':
   assert cache(u)['text']==a['text'];hits+=1
   if hits==3:break
 print('CACHE_VERIFIED',identity,hits)
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 used=db.execute('select coalesce(sum(coalesce(c.charged,c.reserved)),0) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=? and s.task_day=?',('plan-f0d530e5eae24fb981e4b191dffeb0ed','2026-10-30')).fetchone()[0]
 print('RECOVERED_TASK_COST_WITH_RESERVATIONS',used)
print('RELEASE',json.dumps(release))

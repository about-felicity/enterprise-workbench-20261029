import json,sys,subprocess,collections
from pathlib import Path
root=Path('/home/user/geo-editorial/runtime-api')
for name in ('settings.json','control.json','api/health.json'):
 path=root/name
 if path.exists():
  v=json.loads(path.read_text());print(name,{k:v[k] for k in v if k in ('paused','reason','message','revision','status','error','error_type','article_budget_cny','daily_budget_cny','max_per_category','start_time')})
counts=collections.Counter((json.loads(p.read_text()).get('stage'),json.loads(p.read_text()).get('state')) for p in (root/'queue').glob('*/ticket.json'))
print('QUEUE',str(counts))
print('ACCEPTED_ARTICLE_RECEIPTS',len(list((root/'articles').glob('*/*/*/receipt.json'))))
sys.path.insert(0,'/opt/monitor')
from monitor_core.analytics import content_index
index=content_index();print('GEO_CONTENT_ENTRIES',len(index));print('ENTRY_SHAPE',list(next(iter(index.values()),{})))
print('CONTENT_STATUS',str(collections.Counter(v.get('fetch_status',v.get('status','unknown')) for v in index.values())))
for v in index.values():
 if any(k in v for k in ('text_path','text_file','content_file')) or (v.get('quality') in ('high','medium')):
  print('EXAMPLE_ENTRY',json.dumps({k:value for k,value in v.items() if k not in ('text','html','body','excerpt')},ensure_ascii=False)[:1900]);break
print('EDITORIAL_MODULE',subprocess.check_output(['/home/user/geo-editorial/venv/bin/python','-c','import geo_source_cards;print(geo_source_cards.__file__)'],text=True).strip())

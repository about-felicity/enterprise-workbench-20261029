import sys,json,hashlib,time,zipfile
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');state=runtime.read(M/'task.json');task=runtime.read(studio.day_path(state['plan_id'],state['date']));rows=[]
for jid in task.get('jobs',{}).values():
 root=runtime.job_root(jid)
 for folder in sorted((root/'days'/state['date']/'jobs').glob('*/*')):
  writer=folder/'writer';path=writer/'draft.md'
  if not path.exists():continue
  ps=path.read_text('utf-8-sig');category=runtime.read(writer/'category.json')
  rows.append({'job':jid,'folder':str(folder),'category':folder.parent.name,'number':int(folder.name),'draft_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'text':ps,'product':runtime.read(writer/'product.json'),'semantic_review':runtime.read(folder/'review/semantic_review.json'),'logic_review':runtime.read(folder/'review/logic_review.json')})
value={'at':time.time(),'count':len(rows),'by_genre':dict(Counter(r['category'] for r in rows)),'articles':rows}
(M/'drafts-for-direct-review.json').write_text(json.dumps(value,ensure_ascii=False,indent=2));print(json.dumps({k:v for k,v in value.items() if k!='articles'},ensure_ascii=False))

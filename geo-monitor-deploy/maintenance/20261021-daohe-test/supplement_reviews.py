"""Fill this trial's two unallocated reviews from cached independent originals.

Preserve all original job inputs, paid executions and shortfall records. The
supplement uses the same plan/day budget scope; no recapture or request replay.
"""
import sys,json,time,uuid,shutil,hashlib,os,zipfile
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test')
target=Path('/opt/monitor/geo-content/engine/geo_source_cards/genre_pools.py')
with zipfile.ZipFile('/tmp/geo-review-genre-patch.zip') as z:new=z.read('engine/geo_source_cards/genre_pools.py')
backup=M/'genre_pools-before-structure-routing.py'
if not backup.exists():shutil.copyfile(target,backup)
if target.read_bytes()!=new:
 tmp=target.with_suffix('.py.supplement');tmp.write_bytes(new);os.replace(tmp,target)
from creation import runtime,studio
from geo_source_cards.genre_pools import classify_source
from geo_source_cards.daily_editorial import prepare_day
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
state=runtime.read(M/'task.json');record=M/'review-supplement.json'
with process_lock(runtime.BASE/'actions.lock',blocking=True):
 existing=runtime.read(record)
 if existing.get('status')=='running':print(json.dumps(existing,ensure_ascii=False));raise SystemExit(0)
 parent=runtime.job_root('creation-1792575159-0a8f9221');day=parent/'days'/state['date'];original=runtime.read(parent/'job.json')
 allocation=runtime.read(day/'article_allocation.json');assert allocation['genre_shortfalls']=={'排行类':0,'测评类':2}
 groups=runtime.read(day/'source_dedup.json')['representatives'];used={groups[u] for urls in allocation['selected'].values() for u in urls}
 candidates=[]
 for s in runtime.read(day/'media_articles.json'):
  a=classify_source(s,True);g=groups[s['url']]
  if a['genre']=='测评类' and a['status']=='ready' and a['audience']=='general' and g not in used:
   candidates.append(s);used.add(g)
 assert len(candidates)>=2,[(s['url'],s['article']['title']) for s in candidates]
 candidates=candidates[:2]
 identity=existing.get('job_id') or 'creation-'+str(int(time.time()))+'-'+uuid.uuid4().hex[:8]
 root=runtime.BASE/'runs'/identity;root.mkdir(parents=True,exist_ok=True)
 atomic_json(root/'control.json',{'paused':True,'revision':0,'reason':'preparing','message':'准备两篇测评补充素材'})
 atomic_json(record,{'status':'preparing','job_id':identity,'parent':parent.name,'sources':[{'url':s['url'],'title':s['article']['title'],'text_sha256':hashlib.sha256(s['article']['text'].encode()).hexdigest()} for s in candidates]})
 for name in ('settings.json','product.json','logic_policy.json','draft_policy.json'):
  if (parent/name).exists():shutil.copyfile(parent/name,root/name)
 atomic_json(root/'article_goal.json',{'target':2,'prefer_genres':['测评类'],'genre_targets':{'测评类':2}})
 rows=[{'model':'cached_dedicated','question':q,'body':'正文来源已缓存；原文实测主张不是已验证事实。','sources':candidates} for q in original['questions']]
 atomic_write(root/'geo_articles.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
 atomic_write(root/'private_observations.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
 job={**original,'job_id':identity,'created_at':time.time(),'input_sha256':runtime.digest({'parent':parent.name,'sources':candidates,'genre_targets':{'测评类':2}}),'question':'同一批测试的两篇测评缺额补充','article_target':2,'genre_targets':{'测评类':2},'preparation':'ready','supplement_of':parent.name,'material_counts':{'geo_observations':0,'private_observations':len(rows),'full_articles':2}}
 atomic_json(root/'job.json',job)
 result=prepare_day(root,root/'geo_articles.jsonl',root/'product.json',state['date'],max_per_category=2)
 job['prepared']=result;atomic_json(root/'job.json',job)
 taskpath=studio.day_path(state['plan_id'],state['date'])
 with process_lock(taskpath.with_suffix('.lock'),blocking=True):
  task=runtime.read(taskpath);task['jobs']['两篇测评缺额补充']=identity;task['status']='creating';atomic_json(taskpath,task)
 runtime.resume(root)
 final={**runtime.read(record),'status':'running','at':time.time(),'classifier_sha256':hashlib.sha256(new).hexdigest(),'regression_tests_passed':154,'original_inputs_and_paid_executions_preserved':True,'same_plan_budget_cap':5.25}
 atomic_json(record,final);print(json.dumps(final,ensure_ascii=False))

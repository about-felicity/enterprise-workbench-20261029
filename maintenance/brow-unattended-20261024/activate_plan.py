"""Expose the unchanged accepted run and update the existing recurring brow plan."""
import json,os,pwd,shutil,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;LIVE=Path('/opt/monitor/geo-content')
sys.path[:0]=[str(LIVE/'engine'),str(LIVE)]
from creation import studio,runtime,materials
from geo_source_cards.runtime import atomic_json,process_lock
assert (LIVE/'maintenance/brow-v2-20261024/deployed.json').is_file()
state=runtime.read(B/'state.json');assert runtime.read(B/'acceptance-status.json').get('phase')=='finished'
source=B/'runtime/runs'/state['job_id'];destination=runtime.BASE/'runs'/state['job_id']
if not destination.exists():
 staged=LIVE/'maintenance/brow-v2-20261024/accepted-run.importing'
 assert not staged.exists(),'Interrupted job import; preserve evidence'
 shutil.copytree(source,staged)
 policy=runtime.read(staged/'rewrite_policy.json');cache=Path(policy['cache_dir'])
 shutil.copytree(cache,staged/'rewrite_cache')
 policy['cache_dir']=str(destination/'rewrite_cache');atomic_json(staged/'rewrite_policy.json',policy)
 staged.rename(destination)
assert len(runtime.articles(destination))==7
with process_lock(studio.day_path(state['plan_id'],state['date']).with_suffix('.lock'),blocking=True):
 task=runtime.read(studio.day_path(state['plan_id'],state['date']))
 task['jobs']['任务问题汇总']=state['job_id'];task['status']='complete'
 task['acceptance_handoff']={'at':time.time(),'original_mode':task['plan']['task_type'],'job_id':state['job_id']}
 task['plan']={**task['plan'],'task_type':'collect_write'}
 atomic_json(studio.day_path(state['plan_id'],state['date']),task)
# Reuse the daily plan, so there is no duplicate daily schedule.
pid='plan-9b827648df6c4bf9b5648db2eaf6079e';old=studio.plan(pid)
backup=LIVE/'maintenance/brow-v2-20261024/recurring-plan.before.json'
if not backup.exists():atomic_json(backup,old)
payload={**old,'product_id':state['product_id'],'questions':state['questions'],'channels':state['channels'],
 'article_target':7,'max_per_category':7,'article_budget_cny':.35,'task_budget_cny':2.45,
 'enabled':True,'frequency':'daily','task_type':'collect_write'}
result=studio.save_plan(payload);root=studio.capture_root(pid);owner=pwd.getpwnam('user')
# Today's old eight-question snapshot remains historical. Prevent it from
# continuing paid writing after the user switched this plan to the new KB.
from geo_source_cards.pipeline_control import pause
old_day_path=studio.day_path(pid,state['date'])
with process_lock(old_day_path.with_suffix('.lock'),blocking=True):
 old_day=runtime.read(old_day_path)
 if old_day and old_day.get('jobs') and state['job_id'] not in old_day['jobs'].values():
  history=LIVE/'maintenance/brow-v2-20261024/old-daily-task.before.json'
  if not history.exists():atomic_json(history,old_day)
  for old_job_id in old_day['jobs'].values():
   old_root=runtime.job_root(old_job_id)
   assert not any(runtime.read(p).get('state')=='REQUESTING' for p in (old_root/'api').rglob('api_state.json'))
   if not runtime.read(old_root/'control.json').get('paused'):
    pause(old_root,'superseded_product_plan','旧知识库任务已由新版七问题计划替代；历史文章与费用保留。')
  atomic_json(old_day_path,{**old_day,'paused':True,'superseded_by_job':state['job_id'],
   'superseded_reason':'新知识库七问题测试已完成；每日新版计划自下一自然日执行'})
with process_lock(materials.SEARCH_POOL/'browser.lock',blocking=False):
 for model in state['channels']:
  folder=root/'profiles/search'/model;target=folder/'scrapling_profile'
  if target.exists():
   assert runtime.read(folder/'migration.json').get('plan_id')==pid
   continue
  seed=Path(state['capture_root'])/'days'/state['date']/model/'collector/profiles/baidu/scrapling_profile'
  assert seed.is_dir() and not any((seed/n).exists() or (seed/n).is_symlink() for n in ('SingletonLock','SingletonSocket'))
  folder.mkdir(parents=True,exist_ok=True)
  temporary=folder/'scrapling_profile.migrating';assert not temporary.exists()
  shutil.copytree(seed,temporary,ignore=lambda p,names:[n for n in names if n.startswith('Singleton') or Path(p,n).is_symlink() or n in {'Cache','Code Cache','GPUCache','Crashpad'}])
  atomic_json(folder/'migration.json',{'version':'creation-search-profile-v1','plan_id':pid,'model':model,'at':time.time(),
   'source_profile':str(seed),'source_completed':True,'source_plan':state['plan_id'],'task_journal_copied':False})
  temporary.rename(target)
 for p in [root/'profiles',*(root/'profiles').rglob('*')]:
  if not p.is_symlink():os.chown(p,owner.pw_uid,owner.pw_gid)
with process_lock(root/'settings.lock',blocking=True):
 cfg=runtime.read(root/'settings.json');atomic_json(root/'settings.json',{**cfg,'search_pool':'creation_only','day_policy':'today_first'})
atomic_json(B/'activation.json',{'job_id':state['job_id'],'articles_visible':7,'recurring_plan_id':pid,
 'questions':state['questions'],'capture_time':payload['capture_time'],'writing_time':payload['writing_time'],
 'changes_take_effect':'next daily capture; existing daily snapshots retained','result':result})
print((B/'activation.json').read_text())

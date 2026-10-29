"""Durable, paced supplemental capture until each question has an article."""
import os,subprocess,time,json,shutil
from pathlib import Path
from . import runtime,materials
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock

def policy():return runtime.read(runtime.BASE/'supplement_policy.json')
def eligible(task,cfg):
 return cfg.get('enabled') and (task['date']>=cfg.get('start_date','9999') or task['daily_task_id'] in cfg.get('include_days',[])) and not task.get('paused') and not task.get('deleted') and not task.get('error') and task['plan'].get('enabled') and task['plan'].get('task_type')!='capture_only'
def state_path(task):
 from . import studio
 return studio.day_path(task['plan']['plan_id'],task['date']).with_suffix('.supplement-state')
def state(task):return runtime.read(state_path(task))
def save(task,data):atomic_json(state_path(task),data)
def pending(task):
 result=[]
 for question in task['plan']['questions']:
  jid=task.get('jobs',{}).get(question)
  if not jid:
   if question in task.get('skipped_questions',{}):result.append(question)
   continue
  root=runtime.job_root(jid);day=runtime.read(root/'days'/task['date']/'day.json')
  if day.get('status') in {'blocked_insufficient_sources','blocked_no_media_articles'} and not runtime.articles(root):result.append(question)
 return result

def refresh(task,question,round_root,attempt):
 from . import studio
 pid=task['plan']['plan_id'];path=studio.day_path(pid,task['date']);jid=task.get('jobs',{}).get(question)
 if jid:
  root=runtime.job_root(jid)
  with process_lock(root/'api/worker.lock',blocking=False):
   day_state=runtime.read(root/'days'/task['date']/'day.json')
   if day_state.get('status') not in {'blocked_insufficient_sources','blocked_no_media_articles'} or list((root/'queue').glob('*/ticket.json')) or runtime.articles(root):return False
   job=runtime.read(root/'job.json');rows=materials.records(task['date'],question,task['plan']['channels'],studio.capture_root(pid))
   if not rows:return False
   backup=root/'supplement-history'/str(attempt);backup.mkdir(parents=True,exist_ok=True)
   for name in ['job.json','private_observations.jsonl']:
    if (root/name).exists():shutil.copy2(root/name,backup/name)
   day=root/'days'/task['date']/'day.json'
   if day.exists():shutil.copy2(day,backup/'day.json');day.unlink()
   atomic_write(root/'private_observations.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
   atomic_json(root/'job.json',{**job,'preparation':'pending','material_shortfall':'','supplement_attempt':attempt})
   runtime.resume(root,check_balance=False)
 else:
  if not materials.records(task['date'],question,task['plan']['channels'],studio.capture_root(pid)):return False
  with process_lock(path.with_suffix('.lock'),blocking=True):
   latest=runtime.read(path);latest.setdefault('skipped_questions',{}).pop(question,None);atomic_json(path,latest)
 return True

def stop(unit):
 subprocess.run(['systemctl','stop',unit],capture_output=True,timeout=20)

def tick(now=None):
 from . import studio
 cfg=policy()
 if not cfg.get('enabled'):return
 now=time.time() if now is None else now
 tasks=[runtime.read(p) for p in (studio.ROOT/'days').glob('*/*.json')]
 tasks.sort(key=lambda t:(t['daily_task_id'] not in cfg.get('include_days',[]),t['date']))
 running=sum(state(t).get('status')=='capturing' for t in tasks)
 for task in tasks:
  p=task['plan'];s=state(task)
  try:current=studio.plan(p['plan_id'],include_deleted=True)
  except (ValueError,FileNotFoundError):continue
  if not eligible(task,cfg) or current.get('deleted_at') or not current.get('enabled'):
   if s.get('status')=='capturing':stop(s['unit']);save(task,{**s,'status':'paused'})
   continue
  if s.get('status')=='capturing':
   root=Path(s['root']);progress=[v for v in materials.progress(task['date'],root) if v['id'] in s['channels']]
   if any(v['blocked'] or v.get('recovery',{}).get('blocked') for v in progress):
    stop(s['unit']);save(task,{**s,'status':'waiting_verification','message':'补采遇到平台验证，保留原会话等待处理'});running-=1;continue
   if progress and all(v.get('settled',0)>=1 for v in progress) and not runtime.read(root/'health.json').get('active_channels'):
    stop(s['unit']);running-=1
    try:refreshed=refresh(task,s['question'],root,s['attempt'])
    except RuntimeError:refreshed=False
    save(task,{**s,'status':'checking_materials' if refreshed else 'waiting','next_at':now+min(1800,60*2**min(s['attempt']-1,5)),'message':'新一轮采集完成，正在检查有效素材' if refreshed else '本轮素材不足，等待下一轮补采'})
   continue
  questions=pending(task)
  if not questions:
   if s and s.get('status') not in {'complete','waiting_verification'} and all(task.get('jobs',{}).get(q) and runtime.articles(runtime.job_root(task['jobs'][q])) for q in p['questions']):save(task,{**s,'status':'complete','message':''})
   if s.get('status')=='checking_materials' and any(runtime.read(runtime.job_root(j)/'job.json').get('preparation')=='ready' for j in task.get('jobs',{}).values()):save(task,{**s,'status':'writing','message':''})
   continue
  if s.get('status')=='checking_materials':
   s={**s,'status':'waiting','message':'本轮仍缺少合格素材，等待轮换补采其他未完成问题'};save(task,s)
  if s.get('status')=='waiting_verification' or s.get('next_at',0)>now or running>=2:continue
  order=p['questions'];last=s.get('question');start=(order.index(last)+1)%len(order) if last in order else 0
  question=next(q for q in order[start:]+order[:start] if q in questions);channels=[m for m in p['channels'] if m in {'baidu_ai','wenxin_card'}]
  if not channels:continue
  origin=studio.capture_root(p['plan_id'])
  original_progress=[v for v in materials.progress(task['date'],origin) if v['id'] in channels]
  if any(v['blocked'] or v.get('recovery',{}).get('blocked') for v in original_progress):
   save(task,{**s,'status':'waiting_verification','message':'采集通道需要处理平台验证，保留原会话'})
   continue
  attempt=s.get('attempt',0)+1;key=runtime.digest(question)[:12]
  root=origin/'supplements'/task['date']/key/('round-'+str(attempt));root.mkdir(parents=True,exist_ok=True)
  settings={'enabled':True,'time':'00:00','start_date':task['date'],'frequency':'once','questions':[question],'rounds':1,'channels':channels,'search_pool':'creation_only','studio_plan':p,'requested_day':task['date']}
  atomic_json(root/'settings.json',settings)
  unit='creation-supplement-'+runtime.digest([task['daily_task_id'],question,attempt])[:24]
  data={'status':'capturing','question':question,'attempt':attempt,'root':str(root),'channels':channels,'unit':unit,'started_at':now,'message':'正在自动补采第'+str(attempt)+'轮'}
  save(task,data)
  command=['systemd-run','--quiet','--collect','--unit='+unit,'--property=KillMode=control-group','--property=Restart=on-failure','--property=RestartSec=30','--setenv=PYTHONPATH=/opt/monitor/geo-content:/opt/monitor/geo-content/engine','--setenv=GEO_CREATION_MATERIAL_ROOT='+str(root),'--setenv=GEO_CREATION_SUPPLEMENT_ORIGIN='+str(origin),'/home/user/geo-editorial/venv/bin/python','-B','-m','creation.materials']
  result=subprocess.run(command,capture_output=True,timeout=20)
  if result.returncode:save(task,{**data,'status':'waiting','next_at':now+60,'message':'补采通道启动失败，稍后重试'})
  else:running+=1


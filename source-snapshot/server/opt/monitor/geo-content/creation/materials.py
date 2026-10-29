"""Creation-only observations. No receiver, PostgreSQL writes, or GEO bridge."""
from datetime import datetime,timedelta
import json,os,re,sqlite3,subprocess,time
from pathlib import Path
from zoneinfo import ZoneInfo
from geo_source_cards.runtime import atomic_json,atomic_write

ROOT=Path(os.environ.get('GEO_CREATION_MATERIAL_ROOT','/opt/monitor/geo-content/materials'))
LEGACY=Path('/home/user/geo-editorial/runtime-api')
GEO=Path('/opt/monitor/geo-capture');ZONE=ZoneInfo('Asia/Shanghai')
CONTENT_BASE=Path('/opt/monitor/geo-content')
SEARCH_POOL=CONTENT_BASE/'search-pool'
CHANNELS={'deepseek':'DeepSeek','baidu_ai':'百度卡片','wenxin_card':'文心卡片'}

def collector_directory(path,owner):
 """Collector user must traverse every private ancestor, including UMask=0077 parents."""
 root=ROOT.resolve();path=Path(path)
 if ROOT.is_symlink() or path.is_symlink() or (path.resolve()!=root and root not in path.resolve().parents):raise ValueError('采集目录不在专用素材目录内')
 base=CONTENT_BASE.resolve()
 if base in root.parents:
  # Only the collector's group gets traversal; no directory listing or world access.
  os.chown(base,-1,owner.pw_gid);base.chmod((base.stat().st_mode&0o770)|0o010)
  current=base
  for part in path.relative_to(base).parts:
   current=current/part
   if current.is_symlink():raise ValueError('专用采集目录不可使用符号链接')
   current.mkdir(exist_ok=True);os.chown(current,owner.pw_uid,owner.pw_gid);current.chmod(0o700)
 else:
  root.mkdir(parents=True,exist_ok=True)
  for current in [root,*reversed([p for p in path.parents if root in p.parents]),path]:
   current.mkdir(parents=True,exist_ok=True);os.chown(current,owner.pw_uid,owner.pw_gid);current.chmod(0o700)
def read(path,default=None):
 try:return json.loads(Path(path).read_text('utf-8-sig'))
 except FileNotFoundError:return {} if default is None else default
def settings():return read(ROOT/'settings.json')
def validate(v):
 if type(v.get('enabled')) is not bool or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',str(v.get('time',''))):raise ValueError('请选择有效的北京时间和定时开关')
 questions=v.get('questions')
 if not isinstance(questions,list) or not 1<=len(questions)<=100 or any(not isinstance(q,str) or not q.strip() or len(q)>2000 or '\n' in q for q in questions):raise ValueError('每行一个问题，最多100题')
 questions=[q.strip() for q in questions]
 if len(set(questions))!=len(questions):raise ValueError('问题有重复，请先去重')
 return {'enabled':v['enabled'],'time':v['time'],'questions':questions}
def save(value):
 from geo_source_cards.runtime import process_lock
 value=validate(value)
 with process_lock(ROOT/'settings.lock',blocking=True):
  old=settings()
  if value['time']==read(GEO/'daily_plan.json').get('time'):raise ValueError('请与主GEO每日开始时间错开')
  atomic_json(ROOT/'settings.json',{**old,**value,'updated_at':time.time()})
 return {'saved':True,'message':'创作专用采集设置已保存；正在执行的当日问题保持原配置'}
def control(action,store_root=None,day=None):
 from geo_source_cards.runtime import process_lock
 root=Path(store_root) if store_root is not None else ROOT
 with process_lock(root/'settings.lock',blocking=True):
  cfg=read(root/'settings.json')
  if action=='resume':
   for path in (root/'days').glob('*/blocked-*.json'):
    block=read(path)
    session=read(GEO/'deepseek_app_session.json') if read(GEO/'deepseek_backend.json').get('backend')=='android' else read(GEO/'profiles/deepseek/geo-session-health.json')
    if block.get('kind')=='login_required' and session.get('last_checkpoint',0)<=block.get('at',0):raise ValueError('请先在GEO采集页完成DeepSeek登录，再继续专用采集')
   for path in (root/'days').glob('*/blocked-*.json'):path.unlink()
  if day is None:cfg['paused']=action=='pause'
  else:
   cfg['paused_day']=day if action=='pause' else ''
   if action=='resume':
    cfg['paused']=False
    if day<datetime.now(ZONE).date().isoformat():cfg['requested_day']=day
  atomic_json(root/'settings.json',cfg)
 return {'paused':action=='pause'}
def records(day,question,channels,store_root=None):
 if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day) or not set(channels)<=set(CHANNELS):raise ValueError('素材日期或通道不正确')
 root=Path(store_root) if store_root is not None else ROOT
 paths=list((LEGACY/'captures'/day).glob('*/observations.jsonl')) if root==ROOT else []
 paths+=list((root/'days'/day).glob('*/results.jsonl'))
 paths+=list((root/'supplements'/day).glob('*/round-*/days/'+day+'/*/results.jsonl'))
 rows=[];seen=set()
 for path in paths:
  for line in path.read_text('utf-8-sig').splitlines():
   if not line.strip():continue
   row=json.loads(line)
   if row.get('question')!=question or row.get('model') not in channels or row.get('body_capture_complete') is False or row.get('availability') in {'supplement_unavailable','no_card'}:continue
   identity=(row.get('model'),row.get('task_id') or row.get('url'),row.get('captured_at'))
   if identity in seen:continue
   seen.add(identity);rows.append(row)
 return rows
def catalog():
 dates=set()
 for base in (LEGACY/'captures',ROOT/'days'):
  if base.exists():dates.update(p.name for p in base.iterdir() if p.is_dir() and re.fullmatch(r'\d{4}-\d{2}-\d{2}',p.name))
 return {'dates':sorted(dates,reverse=True),'questions':settings().get('questions',[]),'channels':[{'id':k,'name':v} for k,v in CHANNELS.items()]}
def progress(day,store_root=None):
 root=Path(store_root) if store_root is not None else ROOT
 result=[]
 for model,label in CHANNELS.items():
  dbpath=root/'days'/day/model/'collector/tasks.sqlite';counts={};missing=[]
  if dbpath.exists():
   with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:
    counts=dict(db.execute('select state,count(*) from captures group by state'))
    missing=[{'question':q,'reason':'未出现AI卡片' if 'card is still missing' in (e or '') else '缺少来源链接' if 'source links are missing' in (e or '') else '多次读取后仍不完整'} for q,e in db.execute("select question,error from captures where state='failed_deferred'")]
  recovery=read(dbpath.parent/'search_recovery.json') if any(s!='completed' and n for s,n in counts.items()) else {}
  recovery={k:recovery[k] for k in ('status','kind','streak','cooldown_until','blocked') if k in recovery}
  result.append({'id':model,'name':label,'completed':counts.get('completed',0),'failed':counts.get('failed_deferred',0),'settled':counts.get('completed',0)+counts.get('failed_deferred',0),'missing':missing,'counts':counts,'recovery':recovery,'blocked':read(root/'days'/day/('blocked-'+model+'.json')),'error':read(root/'days'/day/('error-'+model+'.json'))})
 return result
def status():
 cfg=settings();now=datetime.now(ZONE);day=now.date().isoformat()
 candidate=datetime.combine(max(now.date(),datetime.strptime(cfg.get('start_date',day),'%Y-%m-%d').date()),datetime.strptime(cfg.get('time','01:00'),'%H:%M').time(),ZONE)
 if candidate<=now:candidate+=timedelta(days=1)
 return {'settings':cfg,'next_run':candidate.isoformat() if cfg.get('enabled') else None,'health':read(ROOT/'health.json'),'progress':progress(day),'storage':'创作中心独立素材库','geo_ingest_enabled':False}

def dedicated_search(model):
 cfg=settings()
 return model in {'baidu_ai','wenxin_card'} and cfg.get('search_pool','creation_only' if cfg.get('studio_plan') else '')=='creation_only' and read(CONTENT_BASE/'creation_search_pool.json').get('enabled') is True

def supplement_origin(root):
 value=os.environ.get('GEO_CREATION_SUPPLEMENT_ORIGIN')
 if not value:return Path(root)
 origin=Path(value).resolve();root=Path(root).resolve()
 if origin.parent!=CONTENT_BASE/'studio/capture' or not origin.name.startswith('plan-') or origin/'supplements' not in root.parents:raise ValueError('Invalid supplemental capture origin')
 return origin

def search_resources(model):
 if dedicated_search(model):
  # Each plan/channel already owns a persistent browser profile. Match its lock
  # and rate state to that identity instead of serializing every plan together.
  resource=supplement_origin(ROOT)/'profiles/search'/model
  return {'lock':resource/'browser.lock','rate':resource/'last_search.json','dedicated':True}
 return {'lock':GEO/'search_browser.lock','rate':GEO/'search_last_start.json','dedicated':False}

def conflict(now,model,geo_plan,busy,*,dedicated=False):
 """No new question while main monitoring runs or its next window is close."""
 if dedicated and model in {'baidu_ai','wenxin_card'}:return None
 if busy:return 'waiting_for_geo'
 if not geo_plan.get('enabled'):return None
 start=datetime.combine(now.date(),datetime.strptime(geo_plan.get('time','05:00'),'%H:%M').time(),ZONE)
 if 0<=(now-start).total_seconds()<300:return 'waiting_for_geo_window'
 if start<=now:start+=timedelta(days=1)
 margin=1800 if model=='deepseek' else 300
 return 'waiting_for_geo_window' if (start-now).total_seconds()<margin else None

class InsufficientMaterials(ValueError):
 pass

def prepare(root,job):
 """Fetch referenced public articles into a private job cache, no GEO writes."""
 from geo_source_cards.editorial_pipeline import prepare as fetch
 from geo_source_cards.article_fetch import MediaScopedFetcher,ScraplingArticleFetcher
 from geo_source_cards.daily_editorial import DEFAULT_MEDIA,prepare_day
 from geo_source_cards.pipeline_control import ensure_running
 input_path=root/'private_observations.jsonl';out=root/('private_source_analysis'+('-supplement-'+str(job['supplement_attempt']) if job.get('supplement_attempt') else ''))
 wrapped=MediaScopedFetcher(ScraplingArticleFetcher(),DEFAULT_MEDIA)
 sources={s['url'] for row in read_lines(input_path) for s in row.get('sources',[])}
 class ObservedFetcher:
  def __init__(self):self.completed=0
  def __call__(self,url):
   atomic_json(root/'material_preparation.json',{'at':time.time(),'phase':'fetching_sources','processed':self.completed,'total':len(sources),'current_url':url})
   result=wrapped(url);self.completed+=1
   atomic_json(root/'material_preparation.json',{'at':time.time(),'phase':'fetching_sources','processed':self.completed,'total':len(sources),'last_status':result.get('status')})
   return result
 fetch(input_path,root/'product.json',out,job['date'],fetcher=ObservedFetcher())
 ensure_running(root)
 rows=[json.loads(line) for line in (out/'articles.jsonl').read_text().splitlines() if line.strip()]
 from .owned_sources import exclude_owned
 rows,owned=exclude_owned(rows,root)
 from geo_source_cards.source_scope import anchors,evaluate
 terms=anchors([job.get('question','')],read(root/'product.json'))
 scoped=[];off_topic=[]
 for row in rows:
  sources=[]
  for source in row.get('sources',[]):
   scope=evaluate(source,terms)
   if scope['status']=='off_topic':off_topic.append({'url':source['url'],'title':source.get('article',{}).get('title') or source.get('title',''),'scope':scope})
   else:sources.append(source)
  if sources:scoped.append({**row,'sources':sources})
 rows=scoped
 atomic_json(root/'off_topic_source_exclusions.json',{'sources':off_topic,'excluded_count':len(off_topic)})
 filtered,full=usable_source_rows(rows)
 minimum=1 if read(root/'rewrite_policy.json').get('workflow')=='rewrite-v2' else 3
 if full<minimum:raise InsufficientMaterials(('已排除'+str(len(owned))+'条自有产品信源；' if owned else '')+('已排除'+str(len(off_topic))+'条跑题来源；' if off_topic else '')+shortfall_message(rows,full,minimum))
 atomic_write(root/'geo_articles.jsonl',''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in filtered))
 if job.get('article_target'):atomic_json(root/'article_goal.json',{'target':job['article_target'],'prefer_genres':['排行类','科普类'],'genre_targets':job.get('genre_targets',{})})
 result=prepare_day(root,root/'geo_articles.jsonl',root/'product.json',job['date'],max_per_category=max(job['max_per_category'],job.get('article_target',0)))
 job.update(preparation='ready',material_counts={'geo_observations':0,'private_observations':len(rows),'full_articles':full},prepared=result)
 atomic_json(root/'job.json',job)
 atomic_json(root/'material_preparation.json',{'at':time.time(),'phase':'ready','full_article_records':full})
 return job

def shortfall_message(rows,full,minimum=3):
 from geo_source_cards.article_quality import normalize
 articles=[s.get('article',{}) for r in rows for s in r.get('sources',[])]
 outside=sum(a.get('status')=='unregistered_media' for a in articles)
 incomplete=sum(a.get('status')!='unregistered_media' and normalize(a).get('status')!='fetched' for a in articles)
 details=[]
 if outside:details.append(str(outside)+'条来源不在当前允许的媒体范围内')
 if incomplete:details.append(str(incomplete)+'条未取得合格完整正文')
 return '可用完整正文'+str(full)+'篇，至少需要'+str(minimum)+'篇'+('（'+'；'.join(details)+'）' if details else '')+'；需补充有效来源'

def usable_source_rows(rows):
 from geo_source_cards.article_quality import normalize
 filtered=[];full=0;seen=set()
 for row in rows:
  sources=[]
  for source in row.get('sources',[]):
   article=normalize(source.get('article',{}))
   url=article.get('final_url') or source.get('url')
   if article.get('status')=='fetched' and url not in seen:
    seen.add(url);sources.append({**source,'article':article})
  if sources:filtered.append({**row,'sources':sources});full+=len(sources)
 return filtered,full

def read_lines(path):return [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]

def main_busy():
 with sqlite3.connect((GEO/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True) as db:services=[r[0] for r in db.execute('select service from jobs where batch in (select current_batch from settings)')]
 for service in services:
  value=subprocess.run(['systemctl','is-active',service],capture_output=True,text=True,timeout=8).stdout.strip()
  if value in {'active','activating','deactivating','reloading'}:return True
 return False

def next_day(cfg,today,now=None):
 if cfg.get('requested_day'):return cfg['requested_day']
 if cfg.get('day_policy')=='today_first' and cfg.get('frequency')=='daily' and today>=cfg['start_date'] and (now or datetime.now(ZONE)).strftime('%H:%M')>=cfg.get('time','01:00'):return today
 for path in sorted((ROOT/'days').glob('*/config.json')):
  day=path.parent.name
  if day>today or cfg.get('paused_day')==day:continue
  plan=read(path);counts={v['id']:v.get('settled',v['completed']) for v in progress(day)}
  if any(counts[m]<len(plan['questions'])*plan.get('rounds',1) for m in plan.get('channels',CHANNELS)):return day
 return cfg['start_date'] if cfg.get('frequency')=='once' else today

def capture_snapshot(target,cfg,owner):
 """Keep immutable contents, granting the collector group read-only access."""
 path=Path(target)/'config.json'
 if not path.exists():atomic_json(path,cfg)
 os.chown(path,-1,owner.pw_gid);path.chmod(0o640)

def run():
 """One-question subprocesses release shared account locks at safe boundaries."""
 from geo_source_cards.runtime import process_lock
 import pwd
 owner=pwd.getpwnam('user');children={};attempts={}
 def private_dir(path):collector_directory(path,owner)
 with process_lock(ROOT/'worker.lock'):
  while True:
   now=datetime.now(ZONE);cfg=settings();day=next_day(cfg,now.date().isoformat(),now);health={'at':time.time(),'day':day,'status':'scheduled'}
   for model,child in list(children.items()):
    process,log,child_day=child
    if process.poll() is None:continue
    code=process.returncode;log.close();del children[model]
    if code==77:atomic_json(ROOT/'days'/child_day/('blocked-'+model+'.json'),{'at':time.time(),'kind':'login_required' if model=='deepseek' else 'verification_required'})
    elif code:
     attempts[model]=time.time()+(5 if code==75 and model!='deepseek' else 60)
     if code!=75:atomic_json(ROOT/'days'/child_day/('error-'+model+'.json'),{'at':time.time(),'exit_code':code,'retry_at':attempts[model],'message':'采集进程异常退出，正在自动重试'})
    else:(ROOT/'days'/child_day/('error-'+model+'.json')).unlink(missing_ok=True)
   try:
    due=day<=now.date().isoformat() and ((ROOT/'days'/day/'config.json').exists() or (cfg.get('enabled') and day>=cfg.get('start_date',day) and (day<now.date().isoformat() or now.strftime('%H:%M')>=cfg.get('time','01:00'))))
    paused=cfg.get('paused') or cfg.get('paused_day')==day
    if due and not paused:
     target=ROOT/'days'/day;private_dir(target)
     capture_snapshot(target,cfg,owner)
     plan=read(target/'config.json');questions=plan['questions'];rounds=plan.get('rounds',1);channels=plan.get('channels',list(CHANNELS));progress_by={v['id']:v for v in progress(day)}
     busy=main_busy();health['status']='running';health['geo_ingest_enabled']=False
     health['search_resource_pool']='creation_only' if dedicated_search('baidu_ai') else 'shared_geo'
     for model in CHANNELS:
      if model not in channels or model in children or progress_by[model].get('settled',progress_by[model]['completed'])>=len(questions)*rounds:continue
      if progress_by[model]['blocked']:
       block=progress_by[model]['blocked'];session=read(GEO/'deepseek_app_session.json')
       if (model=='deepseek' and read(GEO/'deepseek_backend.json').get('backend')=='android'
           and block.get('kind')=='login_required' and session.get('status')=='ready'
           and session.get('last_checkpoint',0)>block.get('at',0)):
        (target/('blocked-'+model+'.json')).unlink(missing_ok=True);progress_by[model]['blocked']={}
       else:health['status']='waiting_login_or_verification';continue
      resources=search_resources(model)
      reason=conflict(now,model,read(GEO/'daily_plan.json'),busy,dedicated=resources['dedicated'])
      if reason:health['status']=reason;continue
      if attempts.get(model,0)>time.time():continue
      if model!='deepseek' and any(m!='deepseek' for m in children):continue
      lane=target/model;private_dir(lane);runtime=lane/'collector';private_dir(runtime)
      qfile=lane/'questions.txt';atomic_write(qfile,'\n'.join(questions)+'\n');os.chown(qfile,owner.pw_uid,owner.pw_gid)
      env={**os.environ,'PYTHONPATH':'','GEO_COLLECTOR_RUNTIME':str(runtime),'GEO_DEEPSEEK_PROFILE_DIR':str(GEO/'profiles/deepseek'),'GEO_DEEPSEEK_PORT':'9514','GEO_DEEPSEEK_RATE_STATE':str(GEO/'deepseek_last_send.json'),'GEO_SEARCH_RATE_STATE':str(resources['rate']),'GEO_UNATTENDED':'1'}
      env.pop('GEO_PIPELINE_ROOT',None)
      env['GEO_DEEPSEEK_SEED_ROOT']=str(GEO/'batches')
      lock=GEO/'deepseek_account.lock' if model=='deepseek' else resources['lock']
      command=['/usr/sbin/runuser','-u','user','--','/usr/bin/flock','-n',str(lock),'/opt/monitor/geo-capture/venv/bin/python','-m','geo_source_cards.cli','--model',model,'--runtime-dir',str(runtime),'--batch','creation-material-'+day+'-'+model,'--questions-file',str(qfile),'--rounds',str(rounds),'--output',str(lane/'results.jsonl'),'--require-sources','--require-complete-sources','--min-deepseek-interval','600','--min-search-interval','60','--max-new-captures','1']
      if resources['dedicated']:
       if supplement_origin(ROOT)==ROOT:private_dir(resources['lock'].parent)
       elif not resources['lock'].parent.is_dir():raise ValueError('Original capture profile has not been initialized')
       adapter=command.index('geo_source_cards.cli');command[adapter-1:adapter+1]=['/opt/monitor/geo-content/bin/search_capture.py']
       command=command[:4]+['/opt/monitor/geo-content/bin/creation-runner','capture',str(SEARCH_POOL/'slots'),str(resources['lock']),'--']+command[7:]
      if model!='deepseek':command+=['--bounded-search-recovery']
      if model=='baidu_ai':command+=['--optional-baidu']
      if model=='deepseek' and read(GEO/'deepseek_backend.json').get('backend')=='android':
       command=['/home/user/redroid-doubao/worker-venv/bin/python','-B','/home/user/redroid-deepseek/code/private_capture.py','--lane',str(lane),'--batch','creation-material-'+day+'-'+model,'--rounds',str(rounds)]
      if model=='deepseek' and read(Path('/opt/monitor/geo-deepseek-browser-test/production.json')).get('enabled') is True:
       command=['/home/user/geo-editorial/venv/bin/python','-B','-m','creation.browser_capture','--lane',str(lane),'--batch','creation-material-'+day+'-'+model,'--rounds',str(rounds)]
       env['PYTHONPATH']='/opt/monitor/geo-content:/opt/monitor/geo-content/engine'
      log=(lane/'capture.log').open('ab');children[model]=(subprocess.Popen(command,env=env,stdout=log,stderr=subprocess.STDOUT),log,day)
     if not children and any(attempts.get(m,0)>time.time() and read(target/('error-'+m+'.json')) for m in channels):health['status']='retrying'
     if not children and any(read(Path(str(search_resources(m)['lock'])+'.waiting.json')) for m in channels if dedicated_search(m)):
      health['status']='waiting_capture_capacity'
     if all(progress_by[m].get('settled',progress_by[m]['completed'])>=len(questions)*rounds for m in channels):
      health['status']='complete'
      if cfg.get('requested_day'):
       with process_lock(ROOT/'settings.lock',blocking=True):
        latest=settings();latest.pop('requested_day',None);atomic_json(ROOT/'settings.json',latest)
    elif paused:health['status']='pausing' if children else 'paused'
    health['active_channels']=list(children)
   except Exception as error:health.update(status='retrying',error_kind=type(error).__name__)
   atomic_json(ROOT/'health.json',health);time.sleep(5)

if __name__=='__main__':run()

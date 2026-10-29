"""Product knowledge, explicit daily plans and durable capture-to-writing orchestration."""
from datetime import datetime,timedelta
import base64,hashlib,io,json,os,re,subprocess,time,uuid,zipfile
from pathlib import Path
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET
from geo_source_cards.runtime import atomic_json,process_lock
from . import runtime,materials

ROOT=Path(os.environ.get('GEO_CREATION_STUDIO_ROOT','/opt/monitor/geo-content/studio'))
ZONE=ZoneInfo('Asia/Shanghai')
def identity(value,prefix):
 if not re.fullmatch(prefix+r'-[a-f0-9]{32}',str(value)):raise ValueError('记录编号不正确')
 return value
def products():return sorted([runtime.read(p) for p in (ROOT/'products').glob('product-*.json')],key=lambda p:p.get('updated_at',0),reverse=True)
def plans():return [v for p in sorted((ROOT/'plans').glob('plan-*.json')) if not (v:=runtime.read(p)).get('deleted_at')]
def plan(value,include_deleted=False):
 value=identity(value,'plan');p=ROOT/'plans'/(value+'.json')
 if not p.is_file():raise ValueError('每日任务配置不存在')
 result=runtime.read(p)
 if result.get('deleted_at') and not include_deleted:raise ValueError('任务已删除，不能再修改或执行')
 return result
def capture_root(value):
 p=plan(value,include_deleted=True)
 return materials.ROOT if p.get('legacy_capture') else ROOT/'capture'/value
def product(value):
 value=identity(value,'product');p=ROOT/'products'/(value+'.json')
 if not p.is_file():raise ValueError('产品知识库不存在')
 return runtime.read(p)
def clock(value):
 if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',str(value)):raise ValueError('请填写有效的北京时间')
 return value
def import_word(payload,analyze_now=True):
 name=payload.get('filename','')
 if not isinstance(name,str) or not name.lower().endswith('.docx'):raise ValueError('请导入.docx Word文件；旧版.doc请先另存为.docx')
 try:body=base64.b64decode(payload.get('content_base64',''),validate=True)
 except Exception:raise ValueError('Word文件编码不正确')
 if not 0<len(body)<=5*1024*1024:raise ValueError('Word文件应小于5MB')
 try:
  with zipfile.ZipFile(io.BytesIO(body)) as z:
   entries=z.infolist()
   if len(entries)>2000 or sum(v.file_size for v in entries)>25*1024*1024:raise ValueError('Word展开后的内容过大')
   xml=z.read('word/document.xml')
   if b'<!DOCTYPE' in xml or b'<!ENTITY' in xml:raise ValueError('不支持包含外部实体的Word')
   tree=ET.fromstring(xml);ns='{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
   lines=[''.join(n.text or '' for n in p.iter(ns+'t')).strip() for p in tree.iter(ns+'p')]
   text='\n'.join(v for v in lines if v)
 except (zipfile.BadZipFile,KeyError,ET.ParseError):raise ValueError('无法读取该Word，请确认是有效的.docx文件')
 if not text:raise ValueError('Word没有可提取文字；扫描图片请先转换成文字版Word')
 if len(text)>120000:raise ValueError('知识库文字超过12万字，请拆分产品文档')
 upload_id='upload-'+uuid.uuid4().hex;folder=ROOT/'imports'/upload_id;folder.mkdir(parents=True)
 (folder/'source.docx').write_bytes(body);(folder/'source.docx').chmod(0o600)
 from .knowledge import analyze
 result={'import_id':upload_id,'filename':Path(name.replace('\\','/')).name[:180],'sha256':hashlib.sha256(body).hexdigest(),'bytes':len(body),'text':text,'paragraphs':len([v for v in lines if v]),'at':time.time(),'analysis':analyze(text,name) if analyze_now else None}
 atomic_json(folder/'extraction.json',result)
 return result
def save_product(payload):
 name=payload.get('name','');brand=payload.get('brand','');audience=payload.get('audience','');facts=payload.get('facts',[])
 if not isinstance(name,str) or not 1<=len(name.strip())<=300 or not isinstance(brand,str) or len(brand)>200 or not isinstance(audience,str) or len(audience)>3000:raise ValueError('请填写产品名称及有效的产品资料')
 if not isinstance(facts,list) or not facts or len(facts)>1000 or any(not isinstance(v,str) or not v.strip() or len(v)>10000 for v in facts) or sum(map(len,facts))>120000:raise ValueError('请确认知识库事实，每行一条，最多1000条/12万字')
 old=product(payload['product_id']) if payload.get('product_id') else {}
 value=old.get('product_id') or 'product-'+uuid.uuid4().hex
 previous={f.get('text'):f for f in old.get('product',{}).get('facts',[])}
 source=old.get('word_source',{})
 if payload.get('import_id'):
  upload=identity(payload['import_id'],'upload');source=runtime.read(ROOT/'imports'/upload/'extraction.json')
  if not source:raise ValueError('Word导入记录不存在，请重新导入')
 doc={**old.get('product',{}),'name':name.strip(),'brand':brand.strip(),'audience':audience.strip(),'demo':False,
      'facts':[previous.get(v.strip()) or {'text':v.strip(),'evidence':('用户导入Word '+source.get('filename','')) if source else '用户在产品知识库输入','approved':True,'approval_scope':'用户提供的产品资料；不代表独立核验或额外功效认证','independently_verified':False} for v in facts]}
 details=payload.get('fact_details',{})
 if not isinstance(details,dict) or not set(details)<=set(facts):raise ValueError('结构化事实必须对应本次产品资料')
 for f in doc['facts']:
  extra=details.get(f['text'])
  if not extra:continue
  report=extra.get('report',{})
  if extra.get('evidence_class')!='supplier_report_summary' or not all(isinstance(report.get(k),str) and report[k].strip() for k in ('id','method','conditions','result','limitation','source_quote')):raise ValueError('检测摘要须包含报告号、方法、条件、结果、适用边界和原句')
  if not source or report['source_quote'] not in source.get('text','') or report['id'] not in source.get('text',''):raise ValueError('检测摘要缺少导入Word中的对应报告编号或原句')
  f.update(evidence_class='supplier_report_summary',report=report)
 if source.get('text'):
  doc['raw_source_text']=source['text']
  doc['raw_source_sha256']=source['sha256']
 version=runtime.digest(doc);result={'product_id':value,'version':version,'product':doc,'word_source':{k:v for k,v in source.items() if k!='text'},'updated_at':time.time()}
 atomic_json(ROOT/'versions'/value/(version+'.json'),result);atomic_json(ROOT/'products'/(value+'.json'),result)
 return {'product_id':value,'version':version,'message':'产品知识库已保存，正在执行的任务保留原知识库版本'}
def complete_product_source(product, product_id, version):
 """Read the original import bound to this exact historical product version."""
 if product.get('raw_source_text') or not product_id or not version:return product
 identity(product_id,'product')
 if not re.fullmatch(r'[a-f0-9]{64}',version):raise ValueError('产品版本不正确')
 snapshot=runtime.read(ROOT/'versions'/product_id/(version+'.json'))
 archived=snapshot.get('product',{})
 if not archived or {k:v for k,v in product.items() if k!='writing_profile'}!={k:v for k,v in archived.items() if k!='writing_profile'}:
  return product
 source=snapshot.get('word_source',{});upload=source.get('import_id')
 if not upload:return product
 identity(upload,'upload')
 original=runtime.read(ROOT/'imports'/upload/'extraction.json')
 if not original or original.get('sha256')!=source.get('sha256'):raise ValueError('原始Word版本校验失败')
 return {**product,'raw_source_text':original['text'],'raw_source_sha256':original['sha256']}

def save_plan(payload):
 kb=product(payload.get('product_id'));old=plan(payload['plan_id']) if payload.get('plan_id') else {}
 qs=payload.get('questions',[]);channels=payload.get('channels',[])
 if not isinstance(qs,list) or not qs or len(qs)>100 or any(not isinstance(q,str) or not q.strip() or len(q)>2000 or '\n' in q for q in qs) or len(set(q.strip() for q in qs))!=len(qs):raise ValueError('请填写不重复的问题，每行一题，最多100题')
 if not isinstance(channels,list) or not channels or not set(channels)<=set(materials.CHANNELS):raise ValueError('请选择有效的采集模型')
 enabled=payload.get('enabled');limit=payload.get('max_per_category',1)
 if type(enabled) is not bool or type(limit) is not int or not 1<=limit<=10:raise ValueError('请确认任务开关和每类篇数（1至10）')
 collect=clock(payload.get('capture_time'));write=clock(payload.get('writing_time'))
 if write<collect:raise ValueError('分析仿写时间应不早于当天采集开始时间')
 if collect==runtime.read(materials.GEO/'daily_plan.json').get('time'):raise ValueError('采集时间需与主GEO开始时间错开')
 start=payload.get('start_date','')
 try:datetime.strptime(start,'%Y-%m-%d')
 except (ValueError,TypeError):raise ValueError('请选择首次执行日期')
 if start<datetime.now(ZONE).date().isoformat() and start!=old.get('start_date'):raise ValueError('首次执行日期不能早于今天')
 rounds=payload.get('rounds',1)
 if type(rounds) is not int or not 1<=rounds<=10:raise ValueError('每题采集轮数须为1至10')
 name=payload.get('name',old.get('name') or kb['product']['name']+'创作任务')
 frequency=payload.get('frequency',old.get('frequency','daily'))
 task_type=payload.get('task_type',old.get('task_type','collect_write'))
 if not isinstance(name,str) or not 1<=len(name.strip())<=120:raise ValueError('请填写任务名称，最多120字')
 if frequency not in {'daily','once'} or task_type not in {'collect_write','capture_only'}:raise ValueError('任务周期或任务类型不正确')
 article_target=payload.get('article_target',old.get('article_target',0))
 if type(article_target) is not int or not 0<=article_target<=100:raise ValueError('任务成稿目标应为1至100篇，留空则沿用每题每类篇数')
 from geo_source_cards.article_allocation import validate_quotas
 from geo_source_cards.product_richness import profile
 genre_targets=validate_quotas(payload.get('genre_targets',old.get('genre_targets')),article_target)
 writing_profile=profile(payload.get('writing_profile',old.get('writing_profile')))
 limits=runtime.pipeline_control.settings(runtime.SHARED)
 budgets={}
 import math
 for key,global_key in [('article_budget_cny','article_budget_cny'),('task_budget_cny','daily_budget_cny')]:
  amount=payload.get(key,old.get(key,limits[global_key]))
  if type(amount) not in (int,float) or not math.isfinite(amount) or not 0<amount<=limits[global_key]:raise ValueError('预算须大于0，且不超过共享限额：单篇'+str(limits['article_budget_cny'])+'元、每日共享'+str(limits['daily_budget_cny'])+'元')
  budgets[key]=float(amount)
 value=old.get('plan_id') or 'plan-'+uuid.uuid4().hex
 result={**old,'plan_id':value,'product_id':kb['product_id'],'product_version':kb['version'],'product':complete_product_source(kb['product'],kb['product_id'],kb['version']),
         'name':name.strip(),'frequency':frequency,'task_type':task_type,'article_target':article_target,'genre_targets':genre_targets,'writing_profile':writing_profile,**budgets,
         'questions':[q.strip() for q in qs],'channels':list(dict.fromkeys(channels)),'rounds':rounds,'capture_time':collect,'writing_time':write,'start_date':start,'enabled':enabled,'max_per_category':limit,'revision':old.get('revision',0)+1,'updated_at':time.time()}
 if writing_profile:result['product']={**result['product'],'writing_profile':writing_profile}
 if old:
  today=datetime.now(ZONE).date().isoformat();captured=runtime.read(capture_root(value)/'days'/today/'config.json')
  if captured:ensure_day(captured.get('studio_plan') or old,today)
 atomic_json(ROOT/'plans'/(value+'.json'),result)
 root=capture_root(value)
 with process_lock(root/'settings.lock',blocking=True):
  cfg=runtime.read(root/'settings.json')
  atomic_json(root/'settings.json',{**cfg,'enabled':enabled,'time':collect,'start_date':start,'frequency':frequency,'timezone':'Asia/Shanghai','questions':result['questions'],'channels':result['channels'],'rounds':rounds,'deepseek_interval':600,'search_interval':60,'studio_plan':result})
 return {'plan_id':value,'message':'任务已保存'+('并加入队列，将按设定时间执行' if enabled else '为草稿，尚未加入执行队列')}

def scheduled_day(p,today):
 return p['start_date'] if p.get('frequency')=='once' else max(today,p['start_date'])
def daily_id(value,day):return value+'--'+day
def day_path(value,day):
 identity(value,'plan')
 if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(day)):raise ValueError('任务日期不正确')
 return ROOT/'days'/day/(value+'.json')
def ensure_day(p,day):
 path=day_path(p['plan_id'],day)
 with process_lock(path.with_suffix('.lock'),blocking=True):
  if not path.exists():atomic_json(path,{'daily_task_id':daily_id(p['plan_id'],day),'date':day,'plan':p,'created_at':time.time(),'jobs':{},'paused':False,'status':'scheduled'})
  task=runtime.read(path)
  captured=runtime.read(capture_root(p['plan_id'])/'days'/day/'config.json')
  if not task.get('jobs'):
   if captured.get('studio_plan'):task['plan']=captured['studio_plan'];atomic_json(path,task)
   elif not captured:task['plan']=p;atomic_json(path,task)
  return task
TERMINAL_JOBS={'complete','complete_with_failures','complete_with_shortfall','blocked_insufficient_sources','blocked_no_media_articles'}
TERMINAL_DAYS={'complete','capture_only_complete','complete_with_failures','insufficient_materials'}

def day_actions(state):
 if state in {'paused','needs_attention','waiting_login'}:return ['day_resume']
 if state in {'collecting','creating','waiting_for_geo','waiting_writing'}:return ['day_pause']
 return []

def delete_plan(payload):
 """Tombstone first; drain sent work and preserve source, output and cost history."""
 p=plan(payload.get('plan_id'),include_deleted=True);value=p['plan_id'];root=capture_root(value)
 atomic_json(ROOT/'plans'/(value+'.json'),{**p,'enabled':False,'deleted_at':p.get('deleted_at') or time.time(),'updated_at':time.time()})
 with process_lock(root/'settings.lock',blocking=True):
  cfg=runtime.read(root/'settings.json');cfg.update(enabled=False,paused=True);cfg.pop('requested_day',None)
  atomic_json(root/'settings.json',cfg)
 for path in (ROOT/'days').glob('*/'+value+'.json'):
  with process_lock(path.with_suffix('.lock'),blocking=True):
   task=runtime.read(path);task.update(paused=True,deleted=True);atomic_json(path,task)
 for path in (runtime.BASE/'runs').glob('*/job.json'):
  if runtime.read(path).get('studio_plan_id')==value:
   runtime.pipeline_control.pause(path.parent,'plan_deleted','任务已删除，已发送请求安全收尾；已有成稿和费用记录保留')
 return {'plan_id':value,'deleted':True,'message':'任务已删除，后续执行已停止。正在处理的请求会安全收尾，已有成稿仍可在“成稿下载”查看。'}

def day_control(payload,pause):
 p=plan(payload.get('plan_id'));day=payload.get('date');day_path(p['plan_id'],day)
 rows=runtime.status()['studio']['daily_tasks']
 row=next((t for t in rows if t['plan_id']==p['plan_id'] and t['date']==day),None)
 if not row or ('day_pause' if pause else 'day_resume') not in day_actions(row['status']):
  raise ValueError('任务状态已变化或本次执行已结束，请刷新查看；已结束的任务不能暂停或继续')
 task=ensure_day(p,day)
 for path in (runtime.BASE/'runs').glob('*/job.json'):
  job=runtime.read(path)
  if job.get('studio_plan_id')==p['plan_id'] and job.get('date')==day:task['jobs'][job['question']]=job['job_id']
 materials.control('pause' if pause else 'resume',store_root=capture_root(p['plan_id']),day=day)
 for jid in task['jobs'].values():
  if pause:runtime.pipeline_control.pause(runtime.job_root(jid),'operator','用户暂停每日创作任务；当前已发送请求安全收尾')
  elif runtime.read(runtime.job_root(jid)/'days'/day/'day.json').get('status') not in TERMINAL_JOBS:runtime.resume(runtime.job_root(jid))
 with process_lock(day_path(p['plan_id'],day).with_suffix('.lock'),blocking=True):
  latest=runtime.read(day_path(p['plan_id'],day));latest['jobs'].update(task['jobs']);latest['paused']=pause
  if not pause:latest.pop('error',None)
  atomic_json(day_path(p['plan_id'],day),latest)
 return {'message':'当日任务已暂停，当前问题/请求安全收尾' if pause else '当日任务继续，已完成内容保留'}
def snapshot(jobs):
 ps=plans();now=datetime.now(ZONE);day=now.date().isoformat();by_id={j['job_id']:j for j in jobs};result=[]
 paths=sorted((ROOT/'days').glob('*/*.json'),reverse=True)[:500]
 active_ids={p['plan_id'] for p in ps}
 tasks=[t for p in paths if (t:=runtime.read(p))['plan']['plan_id'] in active_ids]
 known={(t['plan']['plan_id'],t['date']) for t in tasks}
 for p in ps:
  candidate=scheduled_day(p,day)
  if (p['plan_id'],candidate) not in known:tasks.append({'date':candidate,'plan':p,'jobs':{},'paused':False,'status':'scheduled' if p['enabled'] else 'not_enabled'})
 for t in tasks:
  p=t['plan'];root=capture_root(p['plan_id']);capture_cfg=runtime.read(root/'days'/t['date']/'config.json') or p
  target=len(capture_cfg['questions'])*capture_cfg.get('rounds',1);progress=[v for v in materials.progress(t['date'],store_root=root) if v['id'] in p['channels']]
  job_ids=set(t.get('jobs',{}).values())|{j['job_id'] for j in jobs if j.get('studio_plan_id')==p['plan_id'] and j['date']==t['date']}
  js=[by_id[jid] for jid in job_ids if jid in by_id];complete=sum(j.get('day',{}).get('status')=='complete' for j in js)
  state=t.get('status','scheduled')
  ended=bool(js) and len(js)>=(1 if p.get('article_target') else len(p['questions'])) and all(j.get('day',{}).get('status') in TERMINAL_JOBS for j in js)
  if ended:
   state='complete' if complete==len(js) else 'complete_with_failures' if any(j.get('day',{}).get('status')=='complete_with_failures' for j in js) else 'insufficient_materials'
  elif p.get('task_type')=='capture_only' and progress and all(v['completed']>=target for v in progress):state='complete'
  elif t.get('paused'):state='paused'
  elif t.get('error'):state='needs_attention'
  elif js and any(j.get('control',{}).get('paused') and j.get('day',{}).get('status') not in TERMINAL_JOBS for j in js):state='needs_attention'
  elif len(js)==(1 if p.get('article_target') else len(p['questions'])) and complete==len(js):state='complete'
  elif js:state='creating'
  elif any(v['blocked'] for v in progress):state='waiting_login'
  elif all(v['completed']>=target for v in progress):state='waiting_writing' if p['enabled'] else 'capture_only_complete'
  elif t['date']==day and (root/'days'/day/'config.json').exists():
   state='waiting_for_geo' if runtime.read(root/'health.json').get('status','').startswith('waiting_for_geo') else 'collecting'
  elif not p['enabled'] and p.get('legacy_capture') and runtime.read(root/'settings.json').get('enabled'):state='capture_only'
  stages={}
  for j in js:
   for key,n in j.get('queue',{}).items():
    if j.get('day',{}).get('status')=='complete' and not key.endswith(':accepted'):continue
    stages[key]=stages.get(key,0)+n
  reason=t.get('error') or '；'.join(j['question']+'：'+str(j.get('control',{}).get('message') or j.get('control',{}).get('reason') or '执行需要处理') for j in js if j.get('control',{}).get('paused') and j.get('day',{}).get('status')!='complete')
  if not reason and not t.get('paused'):
   waiting=[]
   for v in progress:
    recovery=v.get('recovery',{})
    if recovery.get('blocked'):waiting.append(v.get('name',v['id'])+'：平台验证需人工处理')
    elif recovery.get('cooldown_until',0)>time.time():
     until=datetime.fromtimestamp(recovery['cooldown_until'],ZONE).strftime('%H:%M:%S')
     waiting.append(v.get('name',v['id'])+'：'+('平台安全验证' if recovery.get('kind')=='verification' else '读取未完成')+'，冷却至北京时间'+until+'后检查')
   reason='；'.join(waiting)
  quality_blocks=[b for j in js for b in j.get('quality_blocks',[])]
  if quality_blocks and state=='complete_with_failures':
   labels={'READY_WITH_LIMITS':'按已有资料继续写作','DEGRADED':'需要调整题目范围','NEED_MORE_EVIDENCE':'资料不足','CONFLICT':'资料相互冲突','REPLAN':'需要重新规划','REVIEW_DISPUTED':'审稿意见待核对','REPAIR_EXHAUSTED':'两轮修订后仍未通过'}
   reason='；'.join(dict.fromkeys(labels.get(b['status'],b['status']) for b in quality_blocks))
  result.append({'daily_task_id':daily_id(p['plan_id'],t['date']),'name':p.get('name',p['product']['name']+'创作任务'),'frequency':p.get('frequency','daily'),'task_type':p.get('task_type','collect_write'),'enabled':p['enabled'],'article_budget_cny':p.get('article_budget_cny'),'task_budget_cny':p.get('task_budget_cny'),'article_target':p.get('article_target',0),'plan_id':p['plan_id'],'date':t['date'],'product':{'name':p['product']['name'],'id':runtime.digest({'name':p['product']['name'],'brand':p['product'].get('brand','')})},'status':state,'capture_time':p['capture_time'],'writing_time':p['writing_time'],'questions':len(p['questions']),'target_per_model':target,'progress':progress,'writing_jobs':len(js),'writing_complete':complete,'articles':sum(len(j['articles']) for j in js),'stages':stages,'error':reason,'jobs':t.get('jobs',{})})
 kbs=products();used={p.get('word_source',{}).get('import_id') for p in kbs}
 pending=[runtime.read(p) for p in (ROOT/'imports').glob('upload-*/extraction.json') if p.parent.name not in used]
 latest=max(pending,key=lambda p:p.get('at',0)) if pending else None
 for item in result:
  item['allowed_actions']=day_actions(item['status'])
  archived=next(t['plan'] for t in tasks if t['plan']['plan_id']==item['plan_id'] and t['date']==item['date'])
  item['article_target']=archived.get('article_target',0)
 from .knowledge_library import summary
 from .product_images import images
 return {'product_images':images(),'knowledge_library':summary(),'products':kbs,'plans':ps,'daily_tasks':result,'today':day,'pending_import':latest,'health':runtime.read(ROOT/'health.json')}
def advance(p,day,now):
 if plan(p['plan_id'],include_deleted=True).get('deleted_at'):return
 task=ensure_day(p,day);path=day_path(p['plan_id'],day)
 if task.get('paused') or task.get('error'):return
 # Today's product/questions are immutable once the daily task has been created.
 p=task['plan'];root=capture_root(p['plan_id']);target=len(p['questions'])*p.get('rounds',1)
 if not p.get('enabled') or p.get('task_type')=='capture_only':return
 progress={v['id']:v for v in materials.progress(day,store_root=root)}
 if (day==now.date().isoformat() and now.strftime('%H:%M')<p['writing_time']) or not all(progress[m]['completed']>=target for m in p['channels']):return
 questions_to_create=['任务问题汇总'] if p.get('article_target') else p['questions']
 for question in questions_to_create:
  task=runtime.read(path)
  if task.get('paused') or task.get('error'):return
  if question in task['jobs']:continue
  payload={'material_source':'dedicated','studio_plan_id':p['plan_id'],'task_name':p.get('name',p['product']['name']+'创作任务'),'budget_limits':{k:p[k] for k in ('article_budget_cny','task_budget_cny') if k in p},'date':day,'question':question,'channels':p['channels'],'max_per_category':p['max_per_category'],'product':p['product']}
  if p.get('article_target'):payload.update(questions=p['questions'],article_target=p['article_target'],genre_targets=p.get('genre_targets',{}))
  try:
   result=runtime.action('new',payload,runtime.digest({'daily_task':task['daily_task_id'],'question':question})[:32])
   with process_lock(path.with_suffix('.lock'),blocking=True):
    task=runtime.read(path);task['jobs'][question]=result['job_id'];task['status']='creating';atomic_json(path,task)
  except Exception as error:
   with process_lock(path.with_suffix('.lock'),blocking=True):
    task=runtime.read(path)
    if not task.get('paused'):
     task['error']='建立创作任务需要处理：'+(str(error)[:180] if isinstance(error,ValueError) else type(error).__name__)
     task['status']='needs_attention';atomic_json(path,task)
   return
def initialize():
 """Migrate existing product and capture settings without enabling paid writing."""
 with process_lock(ROOT/'initialize.lock',blocking=True):
  if (ROOT/'initialized.json').exists():return
  original=runtime.read(runtime.SHARED/'product.json');cfg=materials.settings()
  if original.get('name') and cfg.get('questions'):
   pid='product-'+uuid.uuid4().hex;version=runtime.digest(original);kb={'product_id':pid,'version':version,'product':original,'word_source':{},'updated_at':time.time()}
   atomic_json(ROOT/'products'/(pid+'.json'),kb);atomic_json(ROOT/'versions'/pid/(version+'.json'),kb)
   value='plan-'+uuid.uuid4().hex
   atomic_json(ROOT/'plans'/(value+'.json'),{'plan_id':value,'product_id':pid,'product_version':version,'product':original,'questions':cfg['questions'],'channels':list(materials.CHANNELS),'rounds':cfg.get('rounds',1),'capture_time':cfg.get('time','01:00'),'writing_time':'04:00','start_date':cfg.get('start_date',datetime.now(ZONE).date().isoformat()),'enabled':False,'legacy_capture':True,'max_per_category':1,'revision':1,'updated_at':time.time()})
  atomic_json(ROOT/'initialized.json',{'at':time.time()})
def run():
 import pwd
 ROOT.mkdir(parents=True,exist_ok=True);ROOT.chmod(0o700);owner=pwd.getpwnam('user');os.chown(ROOT,owner.pw_uid,owner.pw_gid);initialize();children={};retry={}
 with process_lock(ROOT/'worker.lock'):
  while True:
   now=datetime.now(ZONE);day=now.date().isoformat();health={'at':time.time(),'status':'ready'}
   try:
    for p in plans():
     value=p['plan_id']
     if not p.get('legacy_capture') and (p.get('enabled') or runtime.read(capture_root(value)/'settings.json').get('requested_day') or any((capture_root(value)/'days').glob('*/config.json'))):
      child=children.get(value)
      if child and child.poll() is not None:children.pop(value);retry[value]=time.time()+60
      if value not in children and retry.get(value,0)<=time.time():
       env={**os.environ,'GEO_CREATION_MATERIAL_ROOT':str(capture_root(value))}
       log_path=ROOT/'capture'/value/'supervisor.log';log_path.parent.mkdir(parents=True,exist_ok=True)
       with log_path.open('ab') as log:children[value]=subprocess.Popen(['/home/user/geo-editorial/venv/bin/python','-B','-m','creation.materials'],env=env,stdout=log,stderr=subprocess.STDOUT)
     task_day=scheduled_day(p,day)
     existing=runtime.read(day_path(value,task_day))
     if task_day<=day and ((p.get('enabled') and day>=p['start_date']) or existing.get('plan',{}).get('enabled')):advance(p,task_day,now)
    for path in sorted((ROOT/'days').glob('*/*.json')):
     old=runtime.read(path)
     if old['date']>=day or old.get('paused') or old.get('error'):continue
     if old['plan'].get('enabled'):
      ids=list(old.get('jobs',{}).values())
      if len(ids)==(1 if old['plan'].get('article_target') else len(old['plan']['questions'])) and all(runtime.read(runtime.job_root(jid)/'days'/old['date']/'day.json').get('status') in ('complete','complete_with_shortfall') for jid in ids):continue
      advance(old['plan'],old['date'],now)
   except Exception as error:health.update(status='needs_attention',error_kind=type(error).__name__)
   atomic_json(ROOT/'health.json',health);time.sleep(10)
if __name__=='__main__':run()

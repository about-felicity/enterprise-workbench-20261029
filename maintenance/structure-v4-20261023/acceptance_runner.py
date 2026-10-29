"""Authorized real structure-only acceptance, frozen v3, canonical historical ledger."""
import copy,hashlib,json,os,shutil,sqlite3,sys,time,traceback,uuid
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
sys.dont_write_bytecode=True
BASE=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-v4-final')
V3=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-recovery-v3-final')
LEGACY=Path('/opt/monitor/geo-content/runtime/acceptance/20261023-structure-real/rank01-structure-real-20261023T141521-70888873')
sys.path[:0]=[str(BASE/'isolated/current/engine'),str(BASE/'isolated/current')]
from creation import runtime
from creation.client import CreationClient
from geo_source_cards import structure_analyzer as sa,structure_protocol as sp
from geo_source_cards.api_budget import BEIJING,INPUT_MISS,OUTPUT,BudgetExceeded
from geo_source_cards.deepseek_api import request_payload
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
import requests
ORIGINAL=runtime.BASE/'runs/creation-1792575159-0a8f9221'
SHARED=runtime.SHARED
NAMES=('writing_prompt.md','writing_job.json','knowledge.json','product.json','writing_task.txt','category.json','batch_rules.md')
META={'date':'2026-10-21','category':'排行类','number':1,'revision':1,'consumer_rewrite':True,
 'acceptance_version':'candidate-structure-recovery-v4-20261023-real-structure-only','known_response_replay':False}
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def emit(root,state,**kw):
 v={'at':time.time(),'state':state,**kw};atomic_json(root/'status.json',v);print(json.dumps(v,ensure_ascii=False),flush=True)
def candidate():
 assert sha(BASE/'manifest.json')=='48c0b5d03142d97dbdb6d98bb663fe3bc3dc3be7cd7ee19bdca5cb91647c3acd'
 m=read(BASE/'manifest.json');assert m['version']=='candidate-structure-recovery-v4-20261023'
 for n,r in m['files'].items():assert sha(BASE/'candidate-source'/n)==r['sha256'],n
 for n,s in m['execution_source_sha256'].items():assert sha(BASE/'isolated/current'/n)==s,n
 assert Path(sp.__file__).resolve()==(BASE/'isolated/current/engine/geo_source_cards/structure_protocol.py').resolve()
 return m
def activity():
 result=[]
 for p in [SHARED,*sorted((runtime.BASE/'runs').iterdir())]:
  if not p.is_dir():continue
  ctl=runtime.read(p/'control.json');job=runtime.read(p/'job.json');active=runtime.read(p/'api/active.json')
  pending=sum(runtime.read(t).get('state') in ('pending','claimed') for t in (p/'queue').glob('*/ticket.json'))
  requesting=active.get('state')=='REQUESTING'
  executable=not ctl.get('paused') and (pending or job.get('preparation')=='pending')
  row={'root':str(p),'paused':ctl.get('paused',False),'active_state':active.get('state'),'pending_claimed':pending,'preparation':job.get('preparation'),'blocks':bool(requesting or executable)}
  result.append(row)
 assert not any(r['blocks'] for r in result),'Other executable/active paid work; do not change shared settings'
 return result
def ledger(root):
 job=read(ORIGINAL/'job.json')
 with sqlite3.connect((SHARED/'api/costs.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row;rows=[dict(r) for r in db.execute('select * from costs order by id')]
  tags=[dict(r) for r in db.execute('select * from studio_cost_scopes order by id')]
 lookup={r['id']:r for r in rows};joined=[{**lookup[t['id']],**t} for t in tags if t['id'] in lookup]
 used=lambda rs:sum(r['charged'] if r['charged'] is not None else r['reserved'] for r in rs)
 article=[r for r in joined if r['job']==job['job_id'] and (r['category']=='' or r['category']=='排行类' and r['article'] in ('shared','1'))]
 scope=[r for r in joined if r['scope']==job['studio_plan_id'] and r['task_day']==job['date']]
 ids={hashlib.sha256(str(p.parent.resolve()).encode()).hexdigest() for p in root.rglob('api_state.json')}
 local=[r for r in joined if r['id'] in ids]
 return {'rows':rows,'tags':tags,'article_used_cny':used(article),'scope_used_cny':used(scope),
  'day_used_cny':used([r for r in rows if r['date']==datetime.now(BEIJING).date().isoformat()]),
  'unknown':[r for r in rows if r['charged'] is None],'article_unknown':[r for r in article if r['charged'] is None],
  'run_rows':local,'run_used_cny':used(local),'run_known_cost_cny':sum(r['charged'] or 0 for r in local)}
def protected():
 src=ORIGINAL/'days/2026-10-21/compiler-pilots/排行类/01'
 paths=[ORIGINAL/'job.json',ORIGINAL/'control.json',BASE/'manifest.json']
 paths += [p for p in src.rglob('*') if p.is_file()]
 paths += [p for p in (BASE/'candidate-source').rglob('*') if p.is_file()]
 paths += [BASE/'isolated/current'/n for n in read(BASE/'manifest.json')['execution_source_sha256']]
 for folder in (runtime.BASE/'acceptance/20261023-rank01-staged/rank01-staged-20261023T120816-e50a98ac/article/writer/structure_calls',):
  paths += [p for p in folder.rglob('*') if p.is_file()]
 paths += [p for p in LEGACY.rglob('*') if p.is_file()]
 paths += [V3/'manifest.json',*[p for p in (V3/'candidate-source').rglob('*') if p.is_file()]]
 return {str(p):sha(p) for p in paths if p.is_file()}
def source(root):return sa.source_input(root/'article/writer',read(root/'article/writer/knowledge.json'))
def check(l,upper):
 return {'article':l['article_used_cny']+upper<=1.02+1e-9,'scope':l['scope_used_cny']+upper<=5.25+1e-9,
  'daily':l['day_used_cny']+upper<=10+1e-9,'incremental':l['run_used_cny']+upper<=.32084764+1e-9,'unknown_clear':not l['article_unknown']}
def prepare():
 m=candidate();active=activity();before=protected();settings=read(SHARED/'settings.json');job=read(ORIGINAL/'job.json')
 tests=read(BASE/'linux-results.json')
 for t in tests:
  if t['suite']!='v3':assert t['exit_code']==0 and not t['failures'] and not t['errors'] and t['network_attempts']==0,t
  else:
   assert len(t['failures'])==1 and len(t['errors'])==2,'Unexpected legacy regression; no paid calls allowed'
   assert 'ambiguous_product_role' in t['failures'][0][0]
   assert all(any(n in e[0] for n in ('compiler_binding_preserves','compact_contract_keeps_complete')) for e in t['errors'])
 assert settings['article_budget_cny']==.35 and settings['daily_budget_cny']==10
 assert job['budget_limits']=={'article_budget_cny':.35,'task_budget_cny':5.25}
 run='rank01-structure-v4-'+datetime.now(BEIJING).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
 root=runtime.BASE/'acceptance/20261023-structure-v4'/run;root.mkdir(parents=True,exist_ok=False)
 w=root/'article/writer';w.mkdir(parents=True);src=ORIGINAL/'days/2026-10-21/compiler-pilots/排行类/01'
 for n in NAMES:shutil.copy2(src/'writer'/n,w/n)
 shutil.copytree(src/'research',root/'article/research')
 isolated=copy.deepcopy(job);isolated['budget_limits']['article_budget_cny']=1.02
 atomic_json(root/'job.json',isolated);atomic_json(root/'settings.json',settings)
 atomic_json(root/'control.json',{'paused':True,'revision':1,'reason':'isolated_structure_preflight'})
 data=source(root);plan=sp.plan(data)
 imports=sp.import_v3_primaries(w,w,data,META,LEGACY,V3)
 reused={r['legacy_call'].split('/')[0] for r in imports}
 pending=[c for c in plan['calls'] if c['key'].split('/')[0] not in reused]
 pending_upper=sum(c['reservation_upper_cny'] for c in pending)
 l=ledger(root);checks=check(l,pending_upper)
 assert len(data['blocks'])==84 and len(plan['units'])==15
 assert all(checks.values()),checks
 assert protected()==before
 auth={'run_id':run,'root':str(root),'at':time.time(),'candidate':m['version'],'manifest_sha256':sha(BASE/'manifest.json'),
  'source_digest':sp.digest(data),'source_blocks':84,'source_regions':15,'input_sha256':{str(p.relative_to(root)):sha(p) for p in root.joinpath('article').rglob('*') if p.is_file()},
  'original_job_id':job['job_id'],'scope':job['studio_plan_id'],'job_before':job,'settings_before':settings,
  'protected_before':before,'ledger_before':l,'activity':active,'plan':plan,'checks':checks,
  'max_new_spend_cny':pending_upper,'pending_calls':pending,'legacy_imports':imports,'legacy_run':str(LEGACY),
  'authorization':'User authorized V4 fixes, explicit reuse of valid historical chunks and completion of only failed/unexecuted structure regions. Prior temporary shared/job article cap 1.02 authorization persists; daily10/scope5.25 unchanged; restore after structure-only execution.'}
 atomic_json(root/'preflight.json',auth)
 emit(root,'preflight_ready',run_id=run,run_path=str(root),reused_primaries=len(imports),pending_calls_upper=len(pending),stage_upper_cny=pending_upper)
def restore(root):
 lease=runtime.read(root/'budget_lease.json')
 if not lease:return
 old=lease['settings_before'];current=read(SHARED/'settings.json')
 done=runtime.read(root/'budget_restoration.json')
 if done.get('shared_exactly_restored') and current==old and read(root/'job.json')==lease['isolated_job_before']:
  return
 with process_lock(SHARED/'control.lock',blocking=True):
  current=read(SHARED/'settings.json')
  assert current['article_budget_cny'] in (1.02,old['article_budget_cny']),'Unexpected operator cap change; preserve and report'
  if current['article_budget_cny']==1.02:atomic_json(SHARED/'settings.json',{**current,'article_budget_cny':old['article_budget_cny']})
 original_job=lease['isolated_job_before']
 atomic_json(root/'job.json',original_job)
 restored=read(SHARED/'settings.json')
 atomic_json(root/'budget_restoration.json',{'at':time.time(),'settings_before':old,'settings_after':restored,
  'shared_exactly_restored':restored==old,'isolated_job_restored':read(root/'job.json')==original_job,
  'original_job_unchanged':sha(ORIGINAL/'job.json')==lease['original_job_sha256']})
 assert restored==old
class GuardBudget(runtime.SharedBudget):
 def __init__(self,root,auth):
  super().__init__(root);self.auth=auth;self.current=None;self.used_keys=set();self.records=[]
 def remaining(self,meta,stage):
  base=super().remaining(meta,stage);l=ledger(self.root)
  return min(base if base is not None else 0,self.auth['max_new_spend_cny']-l['run_used_cny'])
 def reserve(self,payload,directory,meta,stage):
  assert stage=='writer' and meta==META
  key=str(Path(directory).relative_to(self.root/'article/writer/structure_calls/compact-v2'))
  c=next(c for c in self.auth['plan']['calls'] if c['key']==key)
  assert key not in self.used_keys,'Never resend a reserved request'
  assert payload==request_payload(sp.prompt(source(self.root),c['units'],c['mode']),c['max_tokens'])
  assert sp.digest(source(self.root))==self.auth['source_digest']
  assert protected()==self.auth['protected_before'],'Input/candidate/historical request changed'
  activity();l=ledger(self.root)
  assert all(check(l,c['reservation_upper_cny']).values()),'Cumulative/incremental budget check failed'
  assert read(SHARED/'settings.json')=={**self.auth['settings_before'],'article_budget_cny':1.02}
  self.current=Path(directory);identity=super().reserve(payload,directory,meta,stage);self.used_keys.add(key)
  self.records.append({'at':time.time(),'key':key,'id':identity,'input_bytes':c['input_bytes'],'max_tokens':c['max_tokens'],'upper_cny':c['reservation_upper_cny']})
  atomic_json(self.root/'reservation_audit.json',self.records)
  emit(self.root,'real_request_reserved',key=key,max_tokens=c['max_tokens'],upper_cny=c['reservation_upper_cny'])
  return identity
class EvidenceSession(requests.Session):
 def __init__(self,root,budget):super().__init__();self.root=root;self.budget=budget;self.calls=[]
 def request(self,method,url,**kwargs):
  assert url in ('https://api.deepseek.com/user/balance','https://api.deepseek.com/chat/completions')
  paid=url.endswith('/chat/completions');folder=self.budget.current if paid else self.root/'balance_checks'/f'{len(self.calls):03d}'
  assert not paid or folder is not None
  row={'method':method,'url':url,'kind':'completion' if paid else 'balance','started':time.time(),'directory':str(folder)}
  self.calls.append(row);atomic_json(self.root/'http_calls.json',self.calls)
  try:
   response=super().request(method,url,**kwargs)
   row.update(status=response.status_code,finished=time.time())
   atomic_write(folder/'http_response_body.txt',response.text)
   atomic_json(folder/'http_response_metadata.json',{'status':response.status_code,'request_id':response.headers.get('x-request-id'),'content_type':response.headers.get('content-type')})
   return response
  except BaseException as e:row.update(error=type(e).__name__,finished=time.time());raise
  finally:atomic_json(self.root/'http_calls.json',self.calls)
def finish(root,auth,status,error,session):
 w=root/'article/writer';structure=runtime.read(w/'article_structure.json');data=source(root)
 validation={'status':'not_complete','passed':False,'source_blocks':len(data['blocks']),'failures':[]}
 if structure.get('status') in {'structure_ready','structure_ready_with_checks'}:
  try:
   sp.verify(structure,data);parts=structure['sections'];ids=[b for s in parts for b in s['source_block_ids']]
   validation.update(status='passed',passed=True,covered_anchors=len(ids),coverage_ratio=len(ids)/len(data['blocks']),
    source_order_exact=ids==[b['id'] for b in data['blocks']],unique_anchors=len(set(ids)),sections=len(parts),
    section_ids_unique=len({s['id'] for s in parts})==len(parts),
    required_regions_exact=[s['id'] for s in parts]==[g['section_id'] for g in auth['plan']['units']],
    unresolved_roles=[{'id':s['id'],'role':s['role'],'role_status':s['role_status'],'review':s['role_review'],'binding_allowed':s['binding_allowed']} for s in parts if s['role_status']=='needs_check' or s['role']=='unknown'],
    products=[{'section':s['id'],'order':s['order'],'anchors':s['anchors'],'topic':s['topic']} for s in parts if s['role']=='subject'],
    source_digest_current=sp.digest(data)==auth['source_digest'])
   assert validation['source_order_exact'] and validation['required_regions_exact']
   assert all(not s['binding_allowed'] for s in parts if s['role_status']=='needs_check')
   validation['complete_with_pending_role_checks']=bool(validation['unresolved_roles'])
   from geo_source_cards.article_compiler import compile_article
   k=read(w/'knowledge.json');pd=read(w/'product.json');baseline=compile_article(k,pd);bound=sa.bind(baseline,structure)
   assert [(s.get('subject'),s['claim_ids']) for s in baseline['sections']]==[(s.get('subject'),s['claim_ids']) for s in bound['sections']]
   own=next(s for s in bound['sections'] if s.get('subject')==pd['name']);assert own['structure_id']=='AS-O0003'
   atomic_json(root/'product_binding_validation.json',{'status':'deterministic_binding_only_no_writer','owned_product':pd['name'],
     'owned_structure_id':own['structure_id'],'claims_and_identity_unchanged':True,'role_review':bound['structure_role_review']})
   status=structure['status']
  except BaseException as e:validation['passed']=False;validation['failures'].append(str(e));status='validation_failed'
 if structure:shutil.copy2(w/'article_structure.json',root/'article_structure.json')
 l=ledger(root);calls=[]
 for p in sorted(w.rglob('request.json')):
  folder=p.parent;req=read(p);answer=runtime.read(folder/'answer.json');state=runtime.read(folder/'api_state.json')
  calls.append({'directory':str(folder.relative_to(root)),'request_sha256':sha(p),'max_tokens':req['max_tokens'],
   'state':state,'finish_reason':answer.get('finish_reason'),'usage':answer.get('usage'),
   'parsed_response_exists':(folder/'response.json').exists(),'accepted':(folder/'accepted.json').exists(),
   'known_failure':runtime.read(folder/'known_failure.json'),'raw_answer_sha256':sha(folder/'answer.json') if (folder/'answer.json').is_file() else None,
   'recovery':'/recover-' in str(folder)})
 http=session.calls if session else []
 newpaid=sum(r['kind']=='completion' for r in http);balance=sum(r['kind']=='balance' for r in http)
 oldrows={r['id']:r for r in auth['ledger_before']['rows']};current={r['id']:r for r in l['rows']}
 history_ok=all(current.get(k)==v for k,v in oldrows.items())
 runids={r['id'] for r in l['run_rows']};newids=set(current)-set(oldrows)
 preservation={'protected_unchanged':protected()==auth['protected_before'],'old_ledger_rows_unchanged':history_ok,
  'new_rows_only_this_run':newids==runids,'unknown_preserved':all(current.get(r['id'])==r for r in auth['ledger_before']['unknown']),
  'new_unknown':[r for r in l['run_rows'] if r['charged'] is None],
  'no_writer_reviewer_repair_deploy':True,'original_job_id':auth['original_job_id'],'scope':auth['scope']}
 atomic_json(root/'structure_validation.json',validation)
 atomic_json(root/'api_calls.json',{'run_id':root.name,'status':status,'real_completion_calls':newpaid,'balance_checks':balance,'requests':calls,'http_calls':http})
 cost={'run_id':root.name,'status':status,'new_cost_known_cny':l['run_known_cost_cny'],'new_used_including_unknown_reserve_cny':l['run_used_cny'],
  'historical_v3_calls':5,'historical_v3_cost_cny':.02588384,'reused_v3_primaries':len(auth['legacy_imports']),
  'stage_reservation_upper_cny':auth['max_new_spend_cny'],'run_rows':l['run_rows'],'history_before':auth['ledger_before'],
  'article_cumulative_after_cny':l['article_used_cny'],'scope_cumulative_after_cny':l['scope_used_cny'],'daily_cumulative_after_cny':l['day_used_cny'],
  'temporary_article_remaining_cny':1.02-l['article_used_cny'],'scope_remaining_cny':5.25-l['scope_used_cny'],
  'daily_remaining_cny':10-l['day_used_cny'],'billing_note':'Canonical usage-based CNY estimate under existing pricing rules; raw provider usage preserved, not a separate invoice.'}
 atomic_json(root/'cost_ledger.json',cost);atomic_json(root/'preservation_audit.json',preservation)
 sections='\n'.join(f"| {s['order']} | {s['id']} | {s['role']} | {s['topic']} | {s['purpose']} | {', '.join(s['moves'])} | {'–'.join(s['anchors'])} |" for s in structure.get('sections',[]))
 restoration=runtime.read(root/'budget_restoration.json')
 summary=f'''# 排行01真实结构分析

run_id：{root.name}。候选：{auth['candidate']}。状态：{status}。

实际 DeepSeek completions 请求 {newpaid} 次，余额检查 {balance} 次。新增已知费用 {l['run_known_cost_cny']:.8f} 元；含未知预留 {l['run_used_cny']:.8f} 元。本阶段执行前保守预留上界 {auth['max_new_spend_cny']:.6f} 元。未调用 Writer、Reviewer、返修、Word 或部署。

主题：{structure.get('article_topic','尚未形成完整结果')}。目的：{structure.get('article_purpose','')}。

覆盖：{validation.get('covered_anchors',0)}/84；完整性校验：{validation['passed']}。原文产品介绍区域数：{len(validation.get('products',[]))}。复用了{len(auth['legacy_imports'])}个V3真实初始答复，其中第四块仅确定性去除重复单锚点；没有使用旧非法恢复答复。待核对角色原样保留：{json.dumps(validation.get('unresolved_roles',[]),ensure_ascii=False)}。它们禁止绑定，不能视为已确认；本次不启动Writer。

| 顺序 | ID | 角色 | 主题 | 作用 | 论证动作 | 原文锚点 |
|---|---|---|---|---|---|---|
{sections}

失败信息：{json.dumps(error,ensure_ascii=False)}。所有已收到原始HTTP响应、模型原文、请求参数、JSON解析结果和已知失败记录均保留在 article/writer/structure_calls/compact-v2。部分结果不视为完整结构。

共享配置精确恢复：{restoration.get('shared_exactly_restored')}；隔离任务配置恢复：{restoration.get('isolated_job_restored')}。历史账本和原稿保留：{preservation}。

尚未验证：正文生成、事实审稿、独立逻辑审稿、仲裁、返修及文章真实质量；本轮结构通过不能代替文章验收。无生产部署。
'''
 atomic_write(root/'acceptance_summary.md',summary)
 result={'run_id':root.name,'status':status,'error':error,'real_completion_calls':newpaid,'balance_checks':balance,
  'known_cost_cny':l['run_known_cost_cny'],'validation':validation,'restoration':restoration,'preservation':preservation}
 atomic_json(root/'summary.json',result)
 emit(root,status,completion_calls=newpaid,known_cost_cny=l['run_known_cost_cny'],coverage=validation.get('covered_anchors',0),restored=restoration.get('shared_exactly_restored'))
 files={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size,'server_path':str(p)} for p in root.rglob('*') if p.is_file() and p.name!='output_manifest.json'}
 atomic_json(root/'output_manifest.json',{'run_id':root.name,'files':files})
def execute(root):
 auth=read(root/'preflight.json');assert not (root/'execution_started.json').exists(),'One shot: never rerun blindly'
 candidate();assert protected()==auth['protected_before'];assert sp.digest(source(root))==auth['source_digest']
 assert read(SHARED/'settings.json')==auth['settings_before']
 assert all(check(ledger(root),auth['max_new_spend_cny']).values())
 status='technical_failure';error=None;client=None;budget=None;session=None
 atomic_json(root/'execution_started.json',{'at':time.time(),'preflight_sha256':sha(root/'preflight.json')})
 try:
  with ExitStack() as stack:
   # Cooperative mutation locks prevent resumes/new jobs/settings changes during
   # the short temporary shared-cap window. No existing request is interrupted.
   for lock in (runtime.BASE/'actions.lock',SHARED/'control.lock',SHARED/'settings.lock'):
    stack.enter_context(process_lock(lock,blocking=True))
   active=activity();atomic_json(root/'activity_before_lease.json',active)
   assert read(SHARED/'settings.json')==auth['settings_before']
   jobbefore=copy.deepcopy(auth['job_before'])
   atomic_json(root/'budget_lease.json',{'at':time.time(),'settings_before':auth['settings_before'],
    'isolated_job_before':jobbefore,'original_job_sha256':sha(ORIGINAL/'job.json'),'temporary_article_cap':1.02})
   atomic_json(SHARED/'settings.json',{**auth['settings_before'],'article_budget_cny':1.02})
   atomic_json(root/'settings.json',{**auth['settings_before'],'article_budget_cny':1.02})
   atomic_json(root/'control.json',{'paused':False,'revision':2,'reason':'authorized_structure_only'})
   budget=GuardBudget(root,auth);assert budget.remaining(META,'writer')+1e-9>=auth['max_new_spend_cny']
   atomic_json(root/'post_lease_preflight.json',{'at':time.time(),'shared':read(SHARED/'settings.json'),'job':read(root/'job.json'),
    'remaining_cny':budget.remaining(META,'writer'),'required_upper_cny':auth['max_new_spend_cny'],'activity':active})
   session=EvidenceSession(root,budget);client=CreationClient(runtime.KEY,budget=budget,session=session)
   emit(root,'real_structure_analysis_started',reused_primaries=len(auth['legacy_imports']),pending_max_calls=len(auth['pending_calls']),pending_upper_cny=auth['max_new_spend_cny'])
   value=sa.analyze(client,root/'article/writer',root/'article/writer',read(root/'article/writer/knowledge.json'),META)
   status=value['status']
 except BaseException as e:
  status='request_unknown' if getattr(e,'uncertain',False) else 'technical_failure'
  error={'type':type(e).__name__,'message':str(e),'code':getattr(e,'code',None),'uncertain':getattr(e,'uncertain',False),'traceback':traceback.format_exc()}
  atomic_json(root/'failure.json',error)
 finally:
  if client:client.close()
  if budget:budget.db.close()
  restore(root)
  atomic_json(root/'control.json',{'paused':True,'revision':3,'reason':'structure_acceptance_finished_no_writer'})
  finish(root,auth,status,error,session)
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='execute':execute(Path(sys.argv[2]))
 elif sys.argv[1]=='restore':restore(Path(sys.argv[2]))
 else:raise ValueError('Unknown action')

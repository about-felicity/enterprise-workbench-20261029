"""One authorized, isolated first draft. Frozen engine; no repair/deployment.

prepare is offline. execute is an explicit one-shot real execution, protected by
the canonical ledger AND a run-local incremental/remaining-stages guard.
"""
import ast,copy,hashlib,json,math,shutil,sqlite3,sys,time,traceback,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path

BASE=Path('/opt/monitor/geo-capture/maintenance/20261023-b2-repair-entry-v2-final')
sys.path[:0]=[str(BASE/'isolated/current/engine'),str(BASE/'isolated/current')]
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards import structure_analyzer as sa,section_writer as sw,article_compiler as ac
from geo_source_cards import consumer_prompts as cp,review_inputs as ri,review_quality as rq
from geo_source_cards import article_logic as al,review_arbitration as arb,quality_checks as qc
from geo_source_cards.deepseek_api import request_payload,APIError
from geo_source_cards.api_budget import BudgetExceeded,INPUT_MISS,OUTPUT,BEIJING
from geo_source_cards.genre_length import policy
from geo_source_cards.product_richness import contract as detail_contract
ORIGINAL=runtime.BASE/'runs/creation-1792575159-0a8f9221'
DAY='2026-10-21';CATEGORY='排行类';CAP=7.20
NAMES=['writing_prompt.md','writing_job.json','knowledge.json','product.json','writing_task.txt','category.json','batch_rules.md']
CAPS={'structure':65536,'sections':77824,'facts':167936,'logic':131072,'arbitration':217088}
META={'date':DAY,'category':CATEGORY,'number':1,'revision':1,'consumer_rewrite':True,'paragraph_repair':False,'acceptance_version':'candidate-b2-repair-entry-v2-20261023-first-draft','known_response_replay':False}
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def emit(root,state,**kw):
 value={'at':time.time(),'state':state,**kw};atomic_json(root/'status.json',value);print(json.dumps(value,ensure_ascii=False),flush=True)
def size(payload):return len(json.dumps(payload['messages'],ensure_ascii=False).encode('utf8'))+256
def cost(n,t):return (n*INPUT_MISS+t*OUTPUT)/1e6
def ledger(root=None):
 job=read(ORIGINAL/'job.json');scope=job.get('studio_plan_id') or job['job_id']
 with sqlite3.connect((runtime.SHARED/'api/costs.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row;rows=[dict(r) for r in db.execute('select * from costs order by id')]
  tags=[dict(r) for r in db.execute('select * from studio_cost_scopes order by id')]
 lookup={r['id']:r for r in rows};joined=[{**lookup[t['id']],**t} for t in tags if t['id'] in lookup and t['scope']==scope and t['task_day']==job['date']]
 used=lambda rs:sum(r['charged'] if r['charged'] is not None else r['reserved'] for r in rs)
 article=[r for r in joined if r['job']==job['job_id'] and (r['category']=='' or r['category']==CATEGORY and r['article'] in ('shared','1'))]
 local=[]
 if root:
  ids={sha_id(p.parent) for p in root.rglob('api_state.json')};local=[r for r in rows if r['id'] in ids]
 return {'rows':len(rows),'article_used_cny':used(article),'scope_used_cny':used(joined),'today_used_cny':used([r for r in rows if r['date']==datetime.now(BEIJING).date().isoformat()]),'unknown':[{'id':r['id'],'state':r['state'],'reserved':r['reserved']} for r in rows if r['charged'] is None],
  'run_rows':local,'run_used_cny':used(local),'run_known_cost_cny':sum(r['charged'] or 0 for r in local),'run_reserved_unknown_cny':sum(r['reserved'] for r in local if r['charged'] is None)}
def sha_id(p):return hashlib.sha256(str(p.resolve()).encode()).hexdigest()
def snapshot():
 src=ORIGINAL/f'days/{DAY}/compiler-pilots/{CATEGORY}/01'
 paths=[ORIGINAL/'job.json',ORIGINAL/'control.json',Path('/opt/monitor/geo-content/runtime/acceptance/20261022-three-agent/control.json')]
 paths += [p for p in src.rglob('*') if p.is_file()]
 paths += [BASE/'manifest.json',*[p for p in (BASE/'candidate-source').rglob('*') if p.is_file()]]
 return {str(p):sha(p) for p in paths if p.is_file()}
def tasks_for(w):
 k,p,c=[read(w/n) for n in ('knowledge.json','product.json','compilation.json')];length=policy(k.get('reference_design'))
 tasks=sw.plan(c,length);detail=detail_contract(p,True)
 for t in tasks:
  if t.get('subject')==p.get('name'):
   if detail:t['target_hanzi']=max(t['target_hanzi'],detail['target_hanzi']);t['product_detail_contract']=detail
   t['commercial_relationship']='本文涉及自有品牌产品。仅在本节简短披露一次，其他章节不重复。'
 sw.bound_lengths(tasks,length);return tasks
def planned(tasks):
 return {'structure':cost(CAPS['structure'],2400),**{'part:'+t['id']:cost(CAPS['sections'],min(2600,max(900,t['target_hanzi']*3+350))) for t in tasks},'facts':cost(CAPS['facts'],1800),'logic':cost(CAPS['logic'],2400)}
def fits(l,upper):
 return {'incremental':l['run_used_cny']+upper<=CAP+1e-9,'article':l['article_used_cny']+upper<=8+1e-9,'scope':l['scope_used_cny']+upper<=12+1e-9,'daily':l['today_used_cny']+upper<=10+1e-9}
def verify_candidate():
 m=read(BASE/'manifest.json');assert m['version']=='candidate-b2-repair-entry-v2-20261023'
 result={}
 for name,row in m['files'].items():
  frozen=BASE/'candidate-source'/name;assert sha(frozen)==row['sha256']
  actual=BASE/'isolated/current'/name
  if not actual.is_file():actual=BASE/'isolated/current/engine'/name
  assert actual.is_file() and sha(actual)==row['sha256'],str(actual)
  result[name]=row['sha256']
 return result
def prepare():
 run='rank01-staged-'+datetime.now(BEIJING).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
 root=runtime.BASE/'acceptance/20261023-rank01-staged'/run;root.mkdir(parents=True,exist_ok=False)
 frozen=verify_candidate();protected=snapshot();before=ledger(root);settings=read(runtime.SHARED/'settings.json')
 assert settings['article_budget_cny']==.35 and settings['daily_budget_cny']==10,'Unexpected current budget configuration'
 active=runtime.read(ORIGINAL/'api/active.json');assert active.get('state') in (None,'SUBMITTED'),'Original active request unresolved'
 assert not any(read(p).get('state') in {'pending','claimed'} for p in (ORIGINAL/'queue').glob('*/ticket.json')),'Original has executable tickets'
 src=ORIGINAL/f'days/{DAY}/compiler-pilots/{CATEGORY}/01';w=root/'article/writer';w.mkdir(parents=True);(root/'article/review').mkdir()
 for n in NAMES:shutil.copy2(src/'writer'/n,w/n)
 shutil.copytree(src/'research',root/'article/research')
 # Only copied current input materials. No old draft, structure, reply or review.
 job=read(ORIGINAL/'job.json');job['budget_limits']={'article_budget_cny':8.0,'task_budget_cny':12.0}
 atomic_json(root/'job.json',job);atomic_json(root/'settings.json',settings);atomic_json(root/'control.json',{'paused':True,'revision':1,'reason':'offline_preflight'})
 c=ac.prepare(w);tasks=tasks_for(w);pending=planned(tasks)
 tree=ast.parse(Path(sa.__file__).read_text('utf8'));expr=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='message' for t in n.targets))
 message=expr.left.value+json.dumps(sa.source_input(w,read(w/'knowledge.json')),ensure_ascii=False,separators=(',',':'))+'\n上次已知格式错误：'
 analyzer_bytes=size(request_payload(message,2400));assert analyzer_bytes<=CAPS['structure']
 # Measure actual claim contract/prompt data before first send; future context
 # is additionally guarded by the existing caps on EVERY real request.
 part_sizes=[{'id':t['id'],'bytes':size(request_payload(sw.prompt(c,tasks,t,[]),0)),'output_tokens':min(2600,max(900,t['target_hanzi']*3+350))} for t in tasks]
 assert all(v['bytes']<=CAPS['sections'] for v in part_sizes)
 checks=fits(before,sum(pending.values()));assert all(checks.values()),checks
 authorization={'run_id':run,'root':str(root),'candidate_version':read(BASE/'manifest.json')['version'],'frozen_sha256':frozen,'protected_before':protected,'settings_before':settings,'ledger_before':before,'incremental_hard_cap_cny':CAP,'article_cap':8,'scope_cap':12,'daily_cap':10,'same_job_id':job['job_id'],'same_scope':job.get('studio_plan_id'),'no_content_repair':True,'stage1_pending':pending,'stage1_upper_cny':sum(pending.values()),'stage1_calls':len(pending),'analyzer_actual_bytes':analyzer_bytes,'section_actual_bytes':part_sizes,'checks':checks,'no_api_calls_during_preflight':True,'revision_history_not_reset':True}
 atomic_json(root/'preflight.json',authorization);atomic_json(root/'candidate-sha256.json',frozen)
 assert snapshot()==protected;emit(root,'preflight_passed',run_id=run,run_path=str(root),stage1_upper_cny=sum(pending.values()),calls=len(pending),checks=checks)

class GuardBudget(runtime.SharedBudget):
 def __init__(self,root,pending):super().__init__(root);self.pending=dict(pending);self.records=[]
 def reserve(self,payload,directory,meta,stage):
  s=str(directory);key,kind=call_kind(directory);n=size(payload)
  if n>CAPS[kind]:raise BudgetExceeded(f'Input ceiling exceeded for {kind}: {n}>{CAPS[kind]}; evidence retained untruncated')
  upper=cost(n,payload['max_tokens']);future={k:v for k,v in self.pending.items() if k!=key}
  l=ledger(self.root);checks=fits(l,upper+sum(future.values()))
  audit={'at':time.time(),'directory':s,'key':key,'actual_input_bytes':n,'output_tokens':payload['max_tokens'],'this_reserve_upper_cny':upper,'future_upper_cny':sum(future.values()),'run_used_cny':l['run_used_cny'],'checks':checks}
  self.records.append(audit);atomic_json(self.root/'reservation-audit.json',self.records)
  if not all(checks.values()):raise BudgetExceeded('Full remaining-stage envelope no longer fits: '+json.dumps(checks))
  ident=super().reserve(payload,directory,meta,stage);self.pending=future
  emit(self.root,'request_reserved',kind=kind,key=key,upper_cny=upper,remaining_stages_cny=sum(future.values()))
  return ident
 def remaining(self,meta,stage):
  shared=super().remaining(meta,stage);return min(shared,CAP-ledger(self.root)['run_used_cny']) if shared is not None else CAP-ledger(self.root)['run_used_cny']
def call_kind(directory):
 parts=Path(directory).parts
 if 'structure_calls' in parts:return 'structure','structure'
 if 'section_calls' in parts:return 'part:'+parts[parts.index('section_calls')+1],'sections'
 if 'fact-call' in parts:return 'facts','facts'
 if 'logic-call' in parts:return 'logic','logic'
 if 'arbitration-call' in parts:return 'arb:'+next((p for p in parts if p.startswith('batch-')),'single'),'arbitration'
 raise BudgetExceeded('Unplanned call path: '+str(directory))
def save_manifest(root):
 w=root/'article/writer';p=w/'section_calls/manifest.json'
 if p.exists():shutil.copy2(p,root/'section_manifest.json')
 for n in ('article_structure.json','claim_ledger.json'):
  if (w/n).exists():shutil.copy2(w/n,root/n)
def partial(root):
 w=root/'article/writer';paths=list((w/'section_calls').glob('*/accepted.json'))
 if not paths:return
 order=['INTRO']+[t['id'] for t in tasks_for(w) if t['id'] not in {'INTRO','END'}]+['END'];values={read(p)['id']:read(p) for p in paths};lines=[]
 for ident in order:
  if ident not in values:continue
  v=values[ident]
  if v.get('title'):lines+=['# '+v['title']]
  if v.get('heading'):lines+=['## '+v['heading']]
  lines += [p['text'] for p in v['paragraphs']]
 atomic_write(root/'rank01_first_draft.md','\n\n'.join(lines)+'\n')
 atomic_json(root/'partial_article_status.json',{'status':'incomplete','included':list(values),'missing':[i for i in order if i not in values],'not_quality_passed':True})
def execute(root):
 root=Path(root);auth=read(root/'preflight.json');assert auth['root']==str(root)
 assert not (root/'execution-started.json').exists(),'One-shot execution already started; inspect durable states, never blindly rerun'
 verify_candidate();assert snapshot()==auth['protected_before'],'Protected inputs changed since preparation'
 old=auth['settings_before'];assert read(runtime.SHARED/'settings.json')==old
 before=ledger(root);checks=fits(before,auth['stage1_upper_cny']);assert all(checks.values()),checks
 atomic_json(root/'execution-started.json',{'at':time.time(),'preflight_sha256':sha(root/'preflight.json'),'ledger_before':before,'checks':checks})
 leased={**old,'article_budget_cny':8.0};budget=None;client=None;status='technical_failure';detail={};lease_started=False
 try:
  with process_lock(runtime.SHARED/'settings.lock',blocking=True):
   assert read(runtime.SHARED/'settings.json')==old;atomic_json(runtime.SHARED/'settings.json',leased);lease_started=True
  atomic_json(root/'settings.json',leased);atomic_json(root/'control.json',{'paused':False,'revision':2,'reason':'authorized_isolated_staged_first_draft_no_repairs'})
  budget=GuardBudget(root,auth['stage1_pending']);client=CreationClient(runtime.KEY,budget=budget)
  w=root/'article/writer';r=root/'article/review';k=read(w/'knowledge.json')
  emit(root,'structure_analysis');structure=sa.analyze(client,w,w,k,META);save_manifest(root)
  if structure.get('degraded'):raise RuntimeError('Fresh model structure analysis failed; saved fallback is not real model acceptance')
  ac.writer_prompt(w);c=read(w/'compilation.json');tasks=tasks_for(w)
  # Binding can alter prompt/targets; re-evaluate all remaining components.
  budget.pending={k:v for k,v in planned(tasks).items() if k!='structure'}
  assert all(fits(ledger(root),sum(budget.pending.values())).values()),'Post-analysis remaining envelope exceeds limits'
  atomic_json(root/'effective-section-plan.json',tasks);save_manifest(root)
  emit(root,'section_generation',components=len(tasks),pending_upper_cny=sum(budget.pending.values()))
  answer=sw.generate(client,w,META);atomic_json(w/'answer.json',answer);save_manifest(root)
  # Preserve the actual generated draft before any later validation can fail.
  doc=answer['document'];lines=['# '+doc['title']]+[p['text'] for p in doc['introduction']]
  for s in doc['sections']:lines+=['## '+s['heading']]+[p['text'] for p in s['paragraphs']]
  lines += [p['text'] for p in doc['conclusion']];atomic_write(root/'rank01_provider_draft.md','\n\n'.join(lines)+'\n')
  from geo_source_cards.api_worker import materialize
  materialize({'stage':'writer','meta':META},w,copy.deepcopy(answer))
  shutil.copy2(w/'draft.md',root/'rank01_first_draft.md');shutil.copy2(w/'article.docx',root/'rank01_first_draft.docx')
  for n in ri.FILES+('knowledge.json','product.json','draft.md'):
   if (w/n).is_file():shutil.copy2(w/n,r/n)
  # Generate deterministic C mapping before binding; no source changes later.
  fact_prompt=cp.build('review',r);atomic_json(r/'review_inputs.json',{'version':ri.VERSION,'sha256':ri.fingerprint(r)})
  emit(root,'fact_review');fact=client.complete(fact_prompt,r/'fact-call',max_tokens=1800,stage='review',meta=META)
  atomic_json(root/'review_fact.json',{'status':'api_returned','raw_result':fact,'request_directory':str(r/'fact-call'),'draft_sha256':sha(w/'draft.md')})
  # Independent request receives the full text/evidence, never the fact verdict.
  emit(root,'logic_review');logic=client.review_logic(r,r/'logic-call',META)
  atomic_json(root/'review_logic.json',logic)
  from geo_source_cards.api_prompts import expand_references
  expanded=expand_references('review',r,copy.deepcopy(fact));expanded['logic_review']=logic
  local=[*qc.findings((r/'draft.md').read_text('utf8'),read(r/'knowledge.json'),read(r/'product.json')),*qc.semantic_candidates((r/'draft.md').read_text('utf8'))]
  data=arb.context(r,expanded,local);batches=[{**data,'proposals':data['proposals'][i:i+3]} for i in range(0,len(data['proposals']),3)]
  arb_plan=[]
  for i,b in enumerate(batches):
   n=size(request_payload(arb.prompt(b),2200));key='arb:'+('single' if len(batches)==1 else f'batch-{i:03d}')
   arb_plan.append({'key':key,'issues':[v['id'] for v in b['proposals']],'input_bytes':n,'output_tokens':2200,'upper_cny':cost(n,2200),'within_input_cap':n<=CAPS['arbitration']})
  upper=sum(v['upper_cny'] for v in arb_plan);l=ledger(root);checks=fits(l,upper)
  atomic_json(root/'arbitration-preflight.json',{'all_opinions_preserved':True,'proposals':data['proposals'],'batches':arb_plan,'total_upper_cny':upper,'ledger':l,'checks':checks})
  if not all(checks.values()) or not all(v['within_input_cap'] for v in arb_plan):
   status='needs_arbitration';detail={'reason':'All-batch arbitration preflight rejected before first arbitration call','checks':checks,'required_upper_cny':upper}
   atomic_json(root/'review_arbitration.json',{'status':'not_started','reason':detail,'unresolved_proposals':data['proposals']});return
  budget.pending={v['key']:v['upper_cny'] for v in arb_plan}
  emit(root,'arbitration_preflight_passed',issues=len(data['proposals']),batches=len(batches),upper_cny=upper)
  final=rq.process(client,r,copy.deepcopy(fact),META);atomic_json(root/'review_final.json',final)
  if final.get('arbitration'):atomic_json(root/'review_arbitration.json',final['arbitration'])
  else:atomic_json(root/'review_arbitration.json',{'status':'not_required','reason':'No fact, logic or deterministic/semantic proposals'})
  rq.verify_final(final,(r/'draft.md').read_text('utf8'),read(r/'knowledge.json'),read(r/'product.json'),location=r)
  if final.get('arbitration'):arb.enforce(final,(r/'draft.md').read_text('utf8'),read(r/'knowledge.json'),read(r/'product.json'),location=r)
  errors=[]
  from geo_source_cards.genre_length import validate as length_validate
  errors+=length_validate((w/'draft.md').read_text('utf8'),k.get('reference_design'))
  errors += [str(v) for v in qc.findings((w/'draft.md').read_text('utf8'),k,read(w/'product.json')) if v.get('certainty')=='confirmed']
  if len((w/'draft.md').read_text('utf8'))>6000:errors+=['Article exceeds 6000 character ceiling']
  passed=not errors and all(final.get('checks',{}).values()) and all(v.get('supported') for v in final.get('claims',[])) and not final.get('failures') and not final.get('review_disputes') and logic['status']=='passed'
  status='quality_passed' if passed else 'needs_revision' if final.get('failures') or errors or not all(final.get('checks',{}).values()) or logic['status']!='passed' else 'needs_check'
  detail={'deterministic_final_errors':errors,'quality_status':final.get('quality_status'),'fact_checks':final.get('checks'),'logic_status':logic['status'],'review_issues':final.get('review_issues',[]),'review_disputes':final.get('review_disputes',[]),'source_fingerprint_current':ri.fingerprint(r),'final_source_binding_verified':True,'no_content_repair_executed':True}
 except BaseException as e:
  detail={'error_type':type(e).__name__,'code':getattr(e,'code',None),'uncertain':getattr(e,'uncertain',False),'message':str(e)[:2500],'traceback':traceback.format_exc()[-6000:]}
  status='request_unknown' if getattr(e,'uncertain',False) else 'technical_failure';atomic_json(root/'failure.json',detail)
 finally:
  save_manifest(root)
  if not (root/'rank01_first_draft.md').exists():
   if (root/'rank01_provider_draft.md').exists():shutil.copy2(root/'rank01_provider_draft.md',root/'rank01_first_draft.md')
   else:partial(root)
  if (root/'rank01_first_draft.md').exists() and not (root/'rank01_first_draft.docx').exists():
   try:
    from geo_source_cards.word_export import export_docx
    export_docx((root/'rank01_first_draft.md').read_text('utf8'),root/'rank01_first_draft.docx')
   except Exception as e:detail['docx_export_failure']=str(e)
  if client:client.close()
  if budget:budget.close()
  if lease_started:
   with process_lock(runtime.SHARED/'settings.lock',blocking=True):
    now=read(runtime.SHARED/'settings.json');restored=dict(now)
    if now.get('article_budget_cny')==8.0:restored['article_budget_cny']=old['article_budget_cny']
    atomic_json(runtime.SHARED/'settings.json',restored)
  atomic_json(root/'settings.json',old);atomic_json(root/'control.json',{'paused':True,'revision':3,'reason':'isolated_first_round_finished_no_content_repairs'})
  after=ledger(root);calls=[]
  for p in sorted(root.rglob('api_state.json')):
   state=read(p);raw=read(p.parent/'answer.json') if (p.parent/'answer.json').exists() else {};calls.append({'directory':str(p.parent),'state':state,'usage':raw.get('usage'),'provider_request_id':raw.get('request_id')})
  costs={'run_id':root.name,'same_job_id':read(root/'job.json')['job_id'],'same_scope':read(root/'job.json').get('studio_plan_id'),'model_requests':calls,'model_request_count':len(calls),'ledger_before':before,'ledger_after':after,'known_cost_cny':after['run_known_cost_cny'],'reserved_unknown_cny':after['run_reserved_unknown_cny'],'incremental_remaining_cny':CAP-after['run_used_cny'],'historical_costs_preserved':True,'pricing':'existing peak/off-peak usage rules; ledger estimate, not provider invoice','no_repairs':True}
  atomic_json(root/'cost_ledger.json',costs)
  final_settings=read(runtime.SHARED/'settings.json');restored_ok=final_settings==old
  # The isolated job also relinquishes its temporary limits after execution.
  j=read(root/'job.json');atomic_json(root/'job-effective-during-run.json',j);atomic_json(root/'job.json',read(ORIGINAL/'job.json'))
  summary={'run_id':root.name,'status':status,'detail':detail,'article_md_exists':(root/'rank01_first_draft.md').exists(),'article_docx_exists':(root/'rank01_first_draft.docx').exists(),'known_cost_cny':after['run_known_cost_cny'],'calls':len(calls),'protected_inputs_unchanged':snapshot()==auth['protected_before'],'settings_restored':restored_ok,'settings_after':final_settings,'no_deployment':True,'no_content_repair':True}
  atomic_json(root/'summary.json',summary)
  atomic_write(root/'acceptance_summary.md','# 排行01首轮真实执行结果\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n\n本次为真实 API 首轮；未执行内容返修、未部署生产。实际费用按现有计价账本记录，含未知请求的预留单列。\n')
  manifest={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in root.rglob('*') if p.is_file() and p.name not in {'SHA256.json','status.json'} and not p.name.endswith('.lock')}
  atomic_json(root/'SHA256.json',manifest);emit(root,'finished',**summary)

if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='execute':
  root=Path(sys.argv[2])
  with process_lock(root/'runner.lock',blocking=False):execute(root)
 else:raise ValueError('prepare or execute only')

"""One real V4 draft and two independent reviews; no analyzer/arbitration/repair."""
import copy,hashlib,importlib.util,json,math,shutil,sys,time,traceback,uuid
from contextlib import ExitStack
from datetime import datetime
from pathlib import Path
sys.dont_write_bytecode=True
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
P=module('writer_plan',Path(__file__).with_name('writer-v4-plan-20261023.py'))
U=module('structure_evidence',Path('/tmp/rank01-structure-v4-acceptance-20261023.py'))
from creation import runtime
from creation.client import CreationClient
from geo_source_cards import article_compiler as ac,structure_analyzer as sa,structure_protocol as sp,section_writer as sw
from geo_source_cards import consumer_prompts as cp,article_logic as al,review_inputs as ri,quality_checks as qc
from geo_source_cards.api_budget import BudgetExceeded,BEIJING
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards.genre_length import validate as length_validate,hanzi,body
from geo_source_cards.product_richness import check as richness_check
from geo_source_cards.argument_plan import digest
ROOT_PARENT=runtime.BASE/'acceptance/20261023-writer-v4-first'
SOURCE=P.SOURCE;ORIGINAL=U.ORIGINAL;SHARED=runtime.SHARED
META={'date':'2026-10-21','category':'排行类','number':1,'revision':1,'consumer_rewrite':True,
 'acceptance_version':'v4-real-first-draft-and-first-fact-logic-no-arbitration-no-repair','known_response_replay':False}
read=P.read;sha=P.sha
def emit(root,state,**kw):
 value={'at':time.time(),'state':state,**kw};atomic_json(root/'status.json',value);print(json.dumps(value,ensure_ascii=False),flush=True)
def protected():
 result=U.protected();result.update({str(p):sha(p) for p in SOURCE.rglob('*') if p.is_file()})
 return result
def checks(l,upper):
 return {'incremental':l['run_used_cny']+upper<=P.NEW_CAP+1e-9,'article':l['article_used_cny']+upper<=8+1e-9,
  'scope':l['scope_used_cny']+upper<=12+1e-9,'daily':l['day_used_cny']+upper<=10+1e-9,
  'unknown_clear':not l['article_unknown'] or all(r['id'] in {x['id'] for x in l['run_rows']} for r in l['article_unknown'])}
def prepare():
 U.candidate();activity=U.activity();before=protected();settings=read(SHARED/'settings.json');job=read(ORIGINAL/'job.json')
 assert settings['article_budget_cny']==.35 and settings['daily_budget_cny']==10
 assert job['budget_limits']=={'article_budget_cny':.35,'task_budget_cny':5.25}
 source_structure=read(SOURCE/'article_structure.json');sp.verify(source_structure,sa.review_source(source_structure))
 old=Path(read(SOURCE/'preflight.json')['legacy_run']);partial=read(old/'partial_structure.json')
 assert len(partial['accepted_sections'])==9
 for original,current in zip(partial['accepted_sections'],source_structure['sections'][:9]):
  assert all(original[k]==current[k] for k in ('section_id','role','role_status','topic','purpose','moves','after','anchors'))
 run='rank01-writer-v4-'+datetime.now(BEIJING).strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
 root=ROOT_PARENT/run;root.mkdir(parents=True,exist_ok=False);w=root/'article/writer';w.mkdir(parents=True)
 for name in U.NAMES:shutil.copy2(SOURCE/'article/writer'/name,w/name)
 shutil.copytree(SOURCE/'article/research',root/'article/research')
 shutil.copy2(SOURCE/'article_structure.json',w/'article_structure.json')
 for name in ('article_structure.json','structure_validation.json','cost_ledger.json'):
  shutil.copy2(SOURCE/name,root/('input_'+name))
 shutil.copy2(old/'partial_structure.json',root/'input_partial_structure.json')
 plan=P.compile_plan(w);l=U.ledger(root);assert not l['article_unknown']
 assert all(checks(l,plan['all_attempts_upper_cny']).values()),checks(l,plan['all_attempts_upper_cny'])
 article_cap=math.ceil((l['article_used_cny']+plan['all_attempts_upper_cny'])*100)/100
 scope_cap=math.ceil((l['scope_used_cny']+plan['all_attempts_upper_cny'])*100)/100
 assert article_cap<=8 and scope_cap<=12
 isolated=copy.deepcopy(job);isolated['budget_limits']={'article_budget_cny':article_cap,'task_budget_cny':scope_cap}
 atomic_json(root/'job.json',isolated);atomic_json(root/'settings.json',settings)
 atomic_json(root/'control.json',{'paused':True,'revision':1,'reason':'writer_preflight_only'})
 atomic_json(w/'compilation.json',plan['contract']);atomic_json(w/'base_compilation.json',plan['base_contract'])
 for name,value in [('evidence_matrix.json',plan['contract']['evidence']),('claim_ledger.json',plan['contract']['claims']),('reasoning_outline.json',plan['contract']['sections'])]:atomic_json(w/name,value)
 atomic_json(root/'execution_plan.json',plan)
 tests=read(P.BASE/'logs/linux-v3.json')
 auth={'run_id':run,'root':str(root),'candidate':'candidate-structure-recovery-v4-20261023','at':time.time(),
  'settings_before':settings,'original_job':job,'temporary_article_cap_cny':article_cap,'temporary_scope_cap_cny':scope_cap,
  'original_job_id':job['job_id'],'scope':job['studio_plan_id'],'ledger_before':l,'protected_before':before,
  'plan_sha256':sha(root/'execution_plan.json'),'runner_sha256':sha(Path(__file__)),'planner_sha256':sha(Path(P.__file__)),
  'structure_file_sha256':sha(w/'article_structure.json'),'knowledge_sha256':sha(w/'knowledge.json'),'product_sha256':sha(w/'product.json'),
  'base_contract_sha256':plan['base_contract']['sha256'],'execution_contract_sha256':plan['contract']['sha256'],
  'all_attempts_upper_cny':plan['all_attempts_upper_cny'],'initial_upper_cny':plan['initial_upper_cny'],'incremental_cap_cny':P.NEW_CAP,
  'activity':activity,'legacy_tests':tests,'legacy_test_impact':'One obsolete all-or-nothing needs_check expectation, two fixtures mutate inputs after analysis; real source/material versions pre-exist and verify; no assertions or quality standards changed.',
  'newest_request':'Writer uses V4; INTRO + 15 regions + END; preserve original product/claim permissions. First independent fact/logic only. No structure calls, arbitration, content repairs or deployment.'}
 assert protected()==before
 atomic_json(root/'preflight.json',auth)
 emit(root,'preflight_passed',root_path=str(root),initial_calls=plan['initial_calls'],max_calls=plan['max_calls'],initial_upper=plan['initial_upper_cny'],all_attempts_upper=plan['all_attempts_upper_cny'],article_cap=article_cap,scope_cap=scope_cap)
def restore(root):
 lease=runtime.read(root/'budget_lease.json')
 if not lease:return
 current=read(SHARED/'settings.json');old=lease['settings_before']
 done=runtime.read(root/'budget_restoration.json')
 if current==old and done.get('restored') and read(root/'job.json')==lease['original_job']:return
 with process_lock(SHARED/'control.lock',blocking=True):
  current=read(SHARED/'settings.json');assert current['article_budget_cny'] in (lease['temporary_article_cap_cny'],old['article_budget_cny'])
  if current['article_budget_cny']==lease['temporary_article_cap_cny']:atomic_json(SHARED/'settings.json',{**current,'article_budget_cny':old['article_budget_cny']})
 atomic_json(root/'job.json',lease['original_job']);atomic_json(root/'settings.json',old)
 after=read(SHARED/'settings.json');atomic_json(root/'budget_restoration.json',{'at':time.time(),'restored':after==old,'settings_before':old,'settings_after':after,'original_job_unchanged':read(ORIGINAL/'job.json')==lease['original_job']})
 assert after==old
class Guard(runtime.SharedBudget):
 def __init__(self,root,auth,plan,phase):
  super().__init__(root);self.auth=auth;self.plan=plan;self.phase=phase;self.current=None;self.session=None
  self.calls=[]
 def remaining(self,meta,stage):
  value=super().remaining(meta,stage);return min(value if value is not None else 0,P.NEW_CAP-U.ledger(self.root)['run_used_cny'])
 def reserve(self,payload,directory,meta,stage):
  assert meta==META;directory=Path(directory);self.current=directory
  assert sha(self.root/'execution_plan.json')==self.auth['plan_sha256'] and sha(Path(__file__))==self.auth['runner_sha256']
  assert sha(Path(P.__file__))==self.auth['planner_sha256']
  assert protected()==self.auth['protected_before'],'Protected source/candidate changed'
  U.activity();l=U.ledger(self.root);n=P.size(payload);future=0
  if self.phase=='writer':
   assert 'section_calls' in directory.parts and stage=='writer'
   ident=directory.parent.name;env=next(e for e in self.plan['envelopes'] if e['id']==ident)
   attempt=int(directory.name.split('-')[-1]);assert attempt<3 and payload['max_tokens']==env['max_tokens']
   assert n<=env['input_byte_ceiling'],'Request exceeds frozen per-component input envelope; evidence not truncated'
   accepted={p.parent.name for p in (self.root/'article/writer/section_calls').glob('*/accepted.json')}
   for e in self.plan['envelopes']:
    if e['id'] in accepted:continue
    attempts_used=len(list((self.root/'article/writer/section_calls'/e['id']).glob('attempt-*/api_state.json')))
    left=max(0,3-attempts_used-(1 if e['id']==ident else 0));future+=left*e['per_request_upper_cny']
   future+=sum(v['upper_cny'] for v in self.plan['review'].values())
  else:
   ident=directory.name.replace('-call','');env=self.plan['review'][ident]
   assert stage=='review' and payload['max_tokens']==env['max_tokens'] and n<=env['input_bytes']
   future=sum(v['upper_cny'] for k,v in self.plan['review'].items() if k!=ident and not (self.root/'article/review'/(k+'-call')/'api_state.json').exists())
  upper=P.cost(n,payload['max_tokens']);check=checks(l,upper+future)
  assert all(check.values()),check
  identity=super().reserve(payload,directory,meta,stage)
  self.calls.append({'directory':str(directory),'id':identity,'input_bytes':n,'max_tokens':payload['max_tokens'],'upper_cny':upper,'remaining_stage_upper_cny':future})
  atomic_json(self.root/(self.phase+'_reservation_audit.json'),self.calls)
  emit(self.root,'request_reserved',phase=self.phase,component=ident,upper_cny=upper,remaining_upper_cny=future)
  return identity
def assemble(root):
 w=root/'article/writer';plan=read(root/'execution_plan.json');complete=[];missing=[]
 for t in plan['tasks']:
  p=w/'section_calls'/t['id']/'accepted.json'
  if p.exists():complete.append((t,read(p)))
  else:missing.append(t['id'])
 if not complete:return None
 lines=[];claim_map=[];annotations=[]
 for task,value in complete:
  if task['id']=='INTRO':lines.append('# '+value['title'])
  elif task['id']!='END':lines.append('## '+value['heading'])
  for para in value['paragraphs']:
   lines.append(para['text']);annotations.append(para)
   if para.get('evidence_ids'):claim_map.append({'text':para['text'],'evidence_ids':para['evidence_ids']})
 draft='\n\n'.join(lines)+'\n';atomic_write(root/'draft.md',draft);atomic_write(w/'draft.md',draft)
 atomic_json(w/'claim_map.json',{'claims':claim_map});atomic_json(w/'knowledge_to_sections.json',{'sections':plan['mapping']})
 atomic_json(w/'statement_annotations.json',{'compilation_sha256':plan['contract']['sha256'],'statements':annotations})
 k=read(w/'knowledge.json');pd=read(w/'product.json');problems=length_validate(draft,k.get('reference_design'))
 if len(draft)>plan['length']['max_chars']:problems.append('全文超过6000字符')
 detail_errors,detail=richness_check(draft,pd,True,claim_map,cp.reader_facts(pd));problems+=detail_errors
 findings=qc.findings(draft,k,pd)
 roster=[s['subject'] for s in plan['contract']['sections'] if s.get('subject')]
 mentions={n:any(n in v.get('heading','')+' '.join(p['text'] for p in v['paragraphs']) for _,v in complete) for n in roster}
 acceptance={'status':'generated_complete' if not missing else 'writer_incomplete','complete':not missing,
  'components_generated':[t['id'] for t,v in complete],'missing_components':missing,'body_sections':sum(t['id'] not in ('INTRO','END') for t,v in complete),
  'expected_body_sections':15,'expected_order':[t['id'] for t in plan['tasks']],'order_correct':[t['id'] for t,v in complete]==[t['id'] for t in plan['tasks'] if t['id'] not in missing],
  'product_roster':roster,'expected_product_count':len(roster),'product_presence':mentions,'owned_structure_id':'AS-O0003',
  'body_hanzi':hanzi(body(draft)),'total_chars':len(draft),'length_errors':problems,'product_detail':detail,
  'deterministic_findings':findings,'pending_roles':['AS-O0070','AS-O0084'],'pending_role_binding_prohibited':True,
  'source_structure_sha256':read(w/'article_structure.json')['sha256'],'execution_contract_sha256':plan['contract']['sha256'],
  'draft_sha256':sha(root/'draft.md'),'not_quality_approved':True}
 atomic_json(root/'writer_acceptance.json',acceptance)
 if not missing:
  atomic_json(w/'writer_done.json',{'status':'first_draft_pending_review','job_id':read(w/'writing_job.json')['job_id'],
   'compilation':plan['contract'],'draft_sha256':sha(w/'draft.md'),'no_arbitration_or_repairs':True})
 return acceptance
def reviews(root,client,plan):
 assert read(root/'writer_acceptance.json')['complete'] and (root/'draft.docx').is_file()
 w=root/'article/writer';r=root/'article/review';r.mkdir(exist_ok=True)
 for n in (*ri.FILES,'knowledge.json','product.json','draft.md'):
  if (w/n).is_file():shutil.copy2(w/n,r/n)
 fact_prompt=cp.build('review',r)
 # Frozen V4 review prompt adapters still have a literal v2 source projection
 # branch. Supply the intact current original explicitly; never drop evidence.
 source=sa.review_source(read(w/'article_structure.json'))
 fact_prompt+='\n本次当前执行合同为15个区域，旧资料提纲只作来源，不覆盖当前执行顺序。保留两处needs_check，不得当作确定产品角色。另返回issues数组，每项含type、severity（major或minor）、span_ids（正文C编号）、quote、reason、evidence_ids、supporting_material和repair；style建议放suggestions，不单独退稿。不要仅凭CL编号认定事实成立。\n当前来源与执行清单：'+json.dumps({'original_article_source':source,'execution_mapping':plan['mapping'],'execution_contract_sha256':plan['contract']['sha256']},ensure_ascii=False,separators=(',',':'))
 logic_data=al.build_input(r);logic_data['original_article_source']=source;logic_data['execution_mapping']=plan['mapping']
 logic_prompt=al.prompt(logic_data)+'\n每条issues另含severity（major或minor）、quote、evidence_ids及supporting_material，保留现有kind、paragraph_ids、reason、repair字段。不确定角色AS-O0070/AS-O0084仍为待核对，不因范围说明自动认定已确认。一般风格建议不单独退稿。'
 for stage,message in [('fact',fact_prompt),('logic',logic_prompt)]:
  env=plan['review'][stage];assert P.size(P.request_payload(message,env['max_tokens']))<=env['input_bytes'],stage+' review input exceeds preserved evidence envelope'
 atomic_json(root/'review_preflight.json',{'draft_sha256':sha(root/'draft.md'),'source_fingerprint':ri.fingerprint(r),
  'fact_input_bytes':P.size(P.request_payload(fact_prompt,3500)),'logic_input_bytes':P.size(P.request_payload(logic_prompt,3500)),
  'both_prompts_prechecked':True,'source_fully_supplied':True,'no_arbitration':True})
 fingerprint=ri.fingerprint(r)
 for stage,message in [('fact',fact_prompt),('logic',logic_prompt)]:
  assert ri.fingerprint(r)==fingerprint and sha(root/'draft.md')==sha(r/'draft.md')
  emit(root,stage+'_review_started')
  try:
   raw=client.complete(message,r/(stage+'-call'),max_tokens=3500,stage='review',meta=META)
   result={'status':'api_returned','raw_result':raw,'draft_sha256':sha(root/'draft.md'),'source_fingerprint':fingerprint,'independent':True,'issues':raw.get('issues',[])}
   if stage=='logic':
    try:result['certificate']=al.certificate(raw,logic_data,al.deterministic_issues((root/'draft.md').read_text('utf8'),read(w/'product.json')));result['status']=result['certificate']['status']
    except (ValueError,TypeError,KeyError) as e:result['status']='review_protocol_incomplete';result['validation_error']=str(e)
   else:
    from geo_source_cards.review_quality import FACT_CHECKS
    valid=isinstance(raw.get('checks'),dict) and set(raw['checks'])==set(FACT_CHECKS) and all(type(v) is bool for v in raw['checks'].values())
    result['status']='needs_revision' if valid and (not all(raw['checks'].values()) or raw.get('failures') or raw.get('issues')) else 'passed_first_review' if valid else 'review_protocol_incomplete'
   atomic_json(root/(stage+'_review.json'),result)
  except BaseException as e:
   atomic_json(root/(stage+'_review_failure.json'),{'status':'request_unknown' if getattr(e,'uncertain',False) else 'review_unavailable_or_technical_failure','type':type(e).__name__,'message':str(e)})
   if getattr(e,'uncertain',False):raise
   # A known fact-review failure never suppresses the independent logic call.
def audit(root,phase,error,session):
 auth=read(root/'preflight.json');l=U.ledger(root);w=root/'article/writer'
 acceptance=runtime.read(root/'writer_acceptance.json')
 if (w/'section_calls/manifest.json').exists():
  manifest=read(w/'section_calls/manifest.json');manifest['execution_mapping']=read(root/'execution_plan.json')['mapping'];manifest['draft_sha256']=sha(root/'draft.md') if (root/'draft.md').exists() else None;atomic_json(root/'writer_manifest.json',manifest)
 calls=[]
 for p in sorted(root.glob('article/*/**/api_state.json')):
  state=read(p);answer=runtime.read(p.parent/'answer.json');calls.append({'directory':str(p.parent),'state':state,'finish_reason':answer.get('finish_reason'),'usage':answer.get('usage'),'request_sha256':sha(p.parent/'request.json') if (p.parent/'request.json').exists() else None,'known_failure':runtime.read(p.parent/'section_failure.json')})
 atomic_json(root/'writer_calls.json',{'run_id':root.name,'requests':[c for c in calls if '/writer/' in c['directory']],'request_count':sum('/writer/' in c['directory'] for c in calls),'raw_responses_preserved':True})
 atomic_json(root/'review_calls.json',{'requests':[c for c in calls if '/review/' in c['directory']]})
 old={v['id']:v for v in auth['ledger_before']['rows']};now={v['id']:v for v in l['rows']}
 preservation={'old_rows_unchanged':all(now.get(k)==v for k,v in old.items()),'protected_unchanged':protected()==auth['protected_before'],
  'unknown_preserved':all(now.get(v['id'])==v for v in auth['ledger_before']['unknown']),
  'new_unknown':[v for v in l['run_rows'] if v['charged'] is None],'original_job_unchanged':read(ORIGINAL/'job.json')==auth['original_job']}
 costs={'run_id':root.name,'known_new_cost_cny':l['run_known_cost_cny'],'new_used_including_unknown_cny':l['run_used_cny'],'run_rows':l['run_rows'],
  'article_cumulative_cny':l['article_used_cny'],'scope_cumulative_cny':l['scope_used_cny'],'day_cumulative_cny':l['day_used_cny'],
  'incremental_authorization_remaining_cny':P.NEW_CAP-l['run_used_cny'],'history_before':auth['ledger_before'],'preservation':preservation,
  'budget_restoration':runtime.read(root/'budget_restoration.json'),'billing_note':'Usage-based estimate using existing prices, not separate provider invoice.'}
 atomic_json(root/'writer_cost_ledger.json',costs)
 fact=runtime.read(root/'fact_review.json');logic=runtime.read(root/'logic_review.json')
 status='writer_incomplete' if not acceptance.get('complete') else 'draft_saved_pending_review' if phase=='writer' else 'first_reviews_completed_needs_user_review'
 if error:status='request_unknown' if error.get('uncertain') else phase+'_technical_failure'
 summary={'run_id':root.name,'phase':phase,'status':status,'error':error,'writer_acceptance':acceptance,
  'fact_status':fact.get('status'),'logic_status':logic.get('status'),'real_model_calls':len(calls),'known_new_cost_cny':l['run_known_cost_cny'],
  'settings_restored':read(SHARED/'settings.json')==auth['settings_before'],'preservation':preservation,'no_structure_calls_no_arbitration_no_repairs_no_deployment':True}
 atomic_json(root/'summary.json',summary);emit(root,status,calls=len(calls),known_cost_cny=l['run_known_cost_cny'],complete=acceptance.get('complete'))
def execute(root,phase):
 auth=read(root/'preflight.json');plan=read(root/'execution_plan.json');U.candidate()
 marker=root/(phase+'_started.json');assert not marker.exists(),'One-shot phase; reconcile saved states instead of resending'
 assert protected()==auth['protected_before'] and read(SHARED/'settings.json')==auth['settings_before']
 if phase=='review':assert (root/'draft.docx').is_file() and read(root/'writer_acceptance.json')['complete']
 l=U.ledger(root);required=plan['all_attempts_upper_cny'] if phase=='writer' else sum(v['upper_cny'] for v in plan['review'].values())
 assert not l['article_unknown'] and all(checks(l,required).values()),checks(l,required)
 atomic_json(marker,{'at':time.time(),'preflight_sha256':sha(root/'preflight.json')})
 error=None;client=None;budget=None;session=None
 try:
  with ExitStack() as stack:
   for lock in (runtime.BASE/'actions.lock',SHARED/'control.lock',SHARED/'settings.lock'):stack.enter_context(process_lock(lock,blocking=True))
   U.activity();assert read(SHARED/'settings.json')==auth['settings_before']
   atomic_json(root/'budget_lease.json',auth)
   atomic_json(SHARED/'settings.json',{**auth['settings_before'],'article_budget_cny':auth['temporary_article_cap_cny']})
   job=copy.deepcopy(auth['original_job']);job['budget_limits']={'article_budget_cny':auth['temporary_article_cap_cny'],'task_budget_cny':auth['temporary_scope_cap_cny']}
   atomic_json(root/'job.json',job);atomic_json(root/'control.json',{'paused':False,'reason':'authorized_'+phase+'_only'})
   budget=Guard(root,auth,plan,phase);assert budget.remaining(META,'writer')+1e-9>=required
   session=U.EvidenceSession(root,budget);client=CreationClient(runtime.KEY,budget=budget,session=session)
   if phase=='writer':
    emit(root,'writer_started',components=len(plan['tasks']))
    try:
     answer=sw.generate(client,root/'article/writer',META,max_attempts=3);atomic_json(root/'writer_answer.json',answer)
    finally:assemble(root)
   else:reviews(root,client,plan)
 except BaseException as e:
  error={'type':type(e).__name__,'message':str(e),'uncertain':getattr(e,'uncertain',False),'traceback':traceback.format_exc()}
  atomic_json(root/(phase+'_failure.json'),error)
 finally:
  if client:client.close()
  if budget:budget.db.close()
  restore(root);atomic_json(root/'control.json',{'paused':True,'reason':phase+'_finished_no_next_phase_auto'})
  if session:shutil.copy2(root/'http_calls.json',root/(phase+'_http_calls.json'))
  audit(root,phase,error,session)
if __name__=='__main__':
 if sys.argv[1]=='prepare':prepare()
 elif sys.argv[1]=='execute':execute(Path(sys.argv[2]),sys.argv[3])
 elif sys.argv[1]=='restore':restore(Path(sys.argv[2]))

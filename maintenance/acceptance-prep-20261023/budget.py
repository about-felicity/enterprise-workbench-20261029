"""Calculate current candidate prompt costs from saved materials, never send."""
import ast,copy,json,math,shutil,sys
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;W=D.parents[1];S=D/'candidate';sys.path[:0]=[str(S/'engine'),str(S)]
from geo_source_cards import structure_analyzer as a,section_writer as sw,article_logic as logic,review_arbitration as arb
from geo_source_cards.article_compiler import compile_article
from geo_source_cards.consumer_prompts import build,evidence_units
from geo_source_cards.deepseek_api import request_payload
from geo_source_cards.api_budget import INPUT_MISS,INPUT_HIT,OUTPUT,PRICE_DATE
from geo_source_cards.genre_length import policy
from geo_source_cards.product_richness import contract as detail_contract
read=lambda p:json.loads(Path(p).read_text('utf8'))
previous=W/'maintenance/candidate-validation-20261023';oldplan=read(previous/'budget-plan.json');sample=read(previous/'replay-results.json')['samples'][0]
oldwork=Path(sample['work_dir']);work=D/'budget-work';work.mkdir(exist_ok=True)
shutil.copytree(oldwork/'research',work/'research',dirs_exist_ok=True)
writer=work/'writer';writer.mkdir(exist_ok=True)
k,p,structure=[read(D/'fixtures'/('ranking01-'+n+'.json')) for n in ('knowledge','product','article_structure')]
for name,value in [('knowledge.json',k),('product.json',p)]: (writer/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')
compiled=a.bind(compile_article(k,p,evidence_units(writer)),structure)
for name,value in [('compilation.json',compiled),('writer_done.json',{'compilation':compiled}),('article_structure.json',structure)]:
 (writer/name).write_text(json.dumps(value,ensure_ascii=False),encoding='utf8')
old=read(previous/'isolated/evidence/api/runs'/sample['run_id']/'answer.json')['document']
lines=['# '+old['title']]+[v['text'] for v in old['introduction']]
for section in old['sections']:lines+=['## '+section['heading']]+[v['text'] for v in section['paragraphs']]
lines += [v['text'] for v in old['conclusion']]
text='\n\n'.join(lines)+'\n';(writer/'draft.md').write_bytes(text.encode('utf8'))
size=lambda message:len(json.dumps(request_payload(message,0)['messages'],ensure_ascii=False).encode('utf8'))+256
def upper(n,t):return (n*INPUT_MISS+t*OUTPUT)/1_000_000
def ceiling(n):return math.ceil((n+16384)/4096)*4096
length=policy(k.get('reference_design'));tasks=sw.plan(compiled,length);detail=detail_contract(p,True)
for task in tasks:
 if task.get('subject')==p['name']:
  if detail:task['target_hanzi']=max(task['target_hanzi'],detail['target_hanzi']);task['product_detail_contract']=detail
  task['commercial_relationship']='本文涉及自有品牌产品。仅在本节简短披露一次，其他章节不重复。'
sw.bound_lengths(tasks,length)
completed=[{'id':'INTRO','title':old['title'],'paragraphs':old['introduction']},*old['sections'],{'id':'END','paragraphs':old['conclusion']}]
revision=(oldwork/'writer/revision_note.txt').read_text('utf8')
writes=[]
for index,task in enumerate(tasks):
 history=completed[:index]
 rejected=completed[index] if index<len(completed) else None
 writes.append({'id':task['id'],'initial_bytes':size(sw.prompt(compiled,tasks,task,history)),
  'repair_bytes':size(sw.prompt(compiled,tasks,task,history,'已知故障：本节需依原始证据纠正',revision,rejected)),
  'output_tokens':min(2600,max(900,task['target_hanzi']*3+350))})
fact_bytes=size(build('review',writer));logic_bytes=size(logic.prompt(logic.build_input(writer)))
historical=read(previous/'isolated/arbitration-input.json');proposals=historical['proposals']
data=arb.context(writer,{'failures':[v.get('reason','待核对意见') for v in proposals]})
data['proposals']=proposals
arb_bytes=max(size(arb.prompt({**data,'proposals':proposals[i:i+3]})) for i in range(0,len(proposals),3))
# The same actual analyzer source prefix + actual saved source data, no model.
tree=ast.parse((S/'engine/geo_source_cards/structure_analyzer.py').read_text('utf8'))
message=next(n.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='message' for t in n.targets))
prefix=message.left.value
structure_bytes=size(prefix+json.dumps(structure['source'],ensure_ascii=False,separators=(',',':'))+'\n上次已知格式错误：')
measured={'structure':structure_bytes,'sections':max(v['initial_bytes'] for v in writes),'facts':fact_bytes,'logic':logic_bytes,'arbitration':arb_bytes}
caps={stage:ceiling(n) for stage,n in measured.items()};caps['sections']=ceiling(max(max(v['initial_bytes'],v['repair_bytes']) for v in writes))
hist=oldplan['empirical_usage_projection'];n=len(tasks);findings=len(proposals);batches=math.ceil(findings/3)
counts={'structure':1,'sections':n,'facts':1,'logic':1,'arbitration':batches}
outputs={'structure':2400,'sections':sum(v['output_tokens'] for v in writes),'facts':1800,'logic':2400,'arbitration':batches*2200}
phases=[]
for stage,count in counts.items():
 h=hist[stage];pred_output=sum(min(v['output_tokens'],h['median_completion_tokens']) for v in writes) if stage=='sections' else count*min(outputs[stage]/count,h['median_completion_tokens'])
 estimate=(count*measured[stage]*h['max_input_token_byte_ratio']*INPUT_MISS+pred_output*OUTPUT)/1e6
 phases.append({'stage':stage,'initial_calls':count,'historical_size_based_estimate_cny':estimate,
  'initial_measured_max_bytes':measured[stage],'conditional_input_byte_ceiling':caps[stage],
  'initial_max_output_tokens_total':outputs[stage],'initial_reservation_upper_cny':upper(count*caps[stage],outputs[stage])})
initial=sum(v['initial_reservation_upper_cny'] for v in phases)
write_upper=upper(n*caps['sections'],outputs['sections'])
review_upper=upper(caps['facts']+caps['logic']+10*caps['arbitration'],1800+2400+10*2200)
structure_upper=upper(2*caps['structure'],4800)
one_repair=structure_upper+3*write_upper+review_upper
total=structure_upper+3*write_upper+review_upper+2*one_repair
repair_estimate=sum(v['historical_size_based_estimate_cny'] for v in phases)
prior=oldplan['samples'][0]
# A paragraph patch is an alternative to section rewriting, not an extra full
# rewrite. Cost-only worst-scope fixture: all saved paragraphs editable, 30
# synthetic issue records; this is neither a diagnosis nor a model judgment.
from geo_source_cards import paragraph_repair
ps=[{**s,'sha256':logic.text_hash(s['text'])} for s in logic.segments(text)]
issues=[{'type':'contradiction','paragraph_ids':[ps[i%len(ps)]['id']],
 'reason':'仅用于计算提示体积的假设返修问题，不是对真实稿件的审稿结论',
 'repair':'按当前材料修订','text':[ps[i%len(ps)]['text']]} for i in range(30)]
spec={'version':'paragraph-repair-v1','base_sha256':logic.text_hash(text),'compiled_contract':compiled,
 'editable_ids':[s['id'] for s in ps],'required_edit_ids':[s['id'] for s in ps],
 'issues':issues,'error':'费用估算占位，不是审稿结论。'*138,'knowledge_sha256':a.digest(k),'product_sha256':a.digest(p),
 'prior_fact_review':{},'repair_route':{'issues':issues,'editable_ids':[s['id'] for s in ps]},
 'allowed_evidence_ids':sorted({e for c in compiled['claims'] for e in c['source_ids']}),'paragraphs':ps}
(writer/'paragraph_repair.json').write_text(json.dumps(spec,ensure_ascii=False),encoding='utf8')
patch_bytes=size(paragraph_repair.prompt(writer));patch_ceiling=ceiling(patch_bytes);patch_max_output=6000
patch_upper=upper(patch_ceiling,patch_max_output)
assert patch_upper<=3*write_upper,'Section envelope no longer covers patch alternative; recompute'
out={'type':'offline_cost_plan_not_authorization','candidate_version':'candidate-b1-b2-v1-20261023','rate_source':'existing candidate api_budget.py only; no external price or balance query',
 'price_date':PRICE_DATE,'rates_cny_per_million':{'input_miss':INPUT_MISS,'input_hit':INPUT_HIT,'output':OUTPUT},
 'cache_hit_or_off_peak_discount_assumed':False,'sample':'排行01','body_sections':n-2,'initial_components':n,'historical_findings':findings,'historical_arbitration_batches':batches,
 'phases':phases,'initial_estimated_cny':sum(v['historical_size_based_estimate_cny'] for v in phases),
 'initial_reservation_upper_cny':initial,'one_full_repair_estimate_cny':repair_estimate,'two_full_repairs_estimate_extra_cny':2*repair_estimate,
 'expected_with_two_full_repairs_cny':sum(v['historical_size_based_estimate_cny'] for v in phases)+2*repair_estimate,
 'analyzer_second_attempt_extra_upper_cny':upper(caps['structure'],2400),'initial_supplements_two_per_component_extra_upper_cny':2*write_upper,
 '30_vs_26_findings_extra_per_review_cny':upper(caps['arbitration'],2200),'one_repair_including_supplements_upper_cny':one_repair,
 'two_repairs_upper_extra_cny':2*one_repair,'conditional_full_upper_cny':total,'conditional_max_calls':6+9*n+36,
 'repair_structure_analysis':{'full_rewrite_calls_per_round_expected':1,'full_rewrite_calls_per_round_maximum':2,
  'two_rounds_extra_upper_cny':2*structure_upper,'patch_branch_calls':0,
  'reason':'api_worker regenerates analyzer artifact in a new full-writer execution; current job inputs do not carry article_structure.json. Paragraph patches use their inherited compiled contract instead.'},
 'paragraph_patch_alternative':{'calls_per_round':1,'known_failure_retries':0,'measured_cost_fixture_bytes':patch_bytes,
  'conditional_input_byte_ceiling':patch_ceiling,'max_output_tokens':patch_max_output,'upper_cny_per_patch':patch_upper,
  'full_scope_fixture_is_synthetic':True,'covered_by_section_repair_envelope':True,
  'note':'A patch replaces the section rewrite branch for that round; it is not added to a full rewrite. Every resulting version still requires fact, logic and arbitration review.'},
 'max_calls_by_stage':{'structure':6,'components_all_versions_including_two_supplements':9*n,'fact_reviews_all_versions':3,'logic_reviews_all_versions':3,'arbitration_batches_all_versions':30},
 'historical_article_spend_cny':prior['historical_article_used_cny'],'current_shared_article_cap_cny':oldplan['current_shared_article_cap_cny'],
 'current_authorized_new_spend_cny':0,'historical_scope_remaining_cny':oldplan['scope_remaining_cny'],'last_observed_balance_cny':oldplan['last_observed_balance_cny'],
 'balance_observed_at':oldplan['balance_observed_at'],'balance_current_verified':False,'balance_query_performed':False,
 'allowed_to_execute':False,'new_api_calls':0,'budget_changed':False,'old_revision_counts_reset':False,
 'hard_stops':['Any new source blocker including non-arbitrated repair source guard','No explicit real acceptance authorization','No effective budget for full review/repair closure; current new spend 0',
 'Per-request reservation or shared/day/scope/article cap exceeded','More than 2 content repairs or 3 known-failure component attempts','Unknown original request: preserve, no resend',
 'Any input byte ceiling exceeded: stop and recompute without truncating evidence','More than 30 findings: stop and recompute, never drop findings','Fact/logic/arbitration service unavailable or technical failure: stop, not quality pass',
 'Current text/source/contract fingerprint differs: stale review cannot pass','Output incomplete or required product missing: no delivery'],
 'limits':{'max_content_repairs':2,'max_component_attempts':3,'max_analyzer_attempts':2,'max_findings_per_review':30,'arbitration_batch_size':3,'fact_logic_arbitration_technical_retries':0},
 'notes':['Historical prose is only a cost/length surrogate, not a generated candidate article.','Prompt sizes recomputed with B1/B2 bound contract including saved original source in arbitration.',
 'The byte ceilings and call limits are proposed execution conditions, not installed global guards or approved spending. Without pre-send size checks this is not an unconditional bound.',
 'Semantic replanning, evidence recollection or API review retries beyond this envelope require a separate plan; no bypass by omitting checks.','Existing original samples already exhausted content revisions; this plan does not authorize a third repair or reset.'],
 'network_attempts':len(offline_guard.blocked)}
(D/'budget-plan.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
(D/'budget-inputs.json').write_text(json.dumps({'components':writes,'measured':measured,'compiled_sha':compiled['sha256']},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({key:out[key] for key in ('initial_estimated_cny','initial_reservation_upper_cny','two_full_repairs_estimate_extra_cny','conditional_full_upper_cny','conditional_max_calls','allowed_to_execute')},indent=2))

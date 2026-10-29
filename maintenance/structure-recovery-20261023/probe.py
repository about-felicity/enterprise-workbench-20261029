"""Saved original/response audit and local protocol simulation; zero inference."""
import difflib,hashlib,json,os,platform,re,shutil,sys
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated/current'
os.environ['GEO_STRUCTURE_FIXTURES']=str(D);os.environ['GEO_OFFLINE_FIXTURES']=str(D/'fixtures')
sys.path[:0]=[str(S/'engine'),str(S),str(D)]
from geo_source_cards import structure_analyzer as a,structure_protocol as p,article_compiler as compiler
from geo_source_cards.deepseek_api import request_payload
from tests.test_structure_recovery import LocalProtocolClient
read=lambda path:json.loads(Path(path).read_text('utf8'))
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
history=D/'history/rank01';original=read(history/'article_structure.json')['source'];historical=[];prompts=[]
for i in range(2):
 folder=history/f'article/writer/structure_calls/attempt-{i}';req=read(folder/'request.json');answer=read(folder/'answer.json');text=answer['content'];message=req['messages'][1]['content'];prompts.append(message)
 try:json.loads(text);error=None
 except json.JSONDecodeError as e:error={'reason':e.msg,'position':e.pos,'line':e.lineno,'column':e.colno,'context':text[max(0,e.pos-36):e.pos+60]}
 historical.append({'request_sha256':sha(folder/'request.json'),'answer_sha256':sha(folder/'answer.json'),'model':req['model'],'response_format':req['response_format'],
  'max_tokens':req['max_tokens'],'finish_reason':answer['finish_reason'],'usage':answer['usage'],'characters':len(text),'json_error':error,
  'last_section_id':re.findall(r'AS\d{3}',text)[-1],'tail':text[-240:],'redundant_verbose_fields':{k:len(re.findall('"'+k+'"',text)) for k in ('purpose','required_content','argument_step','transition','source_quote')}})
audit={'type':'saved_real_request_audit_no_new_calls','historical':historical,'retry_protocol_and_ceiling_unchanged':prompts[1]==prompts[0]+'output_incomplete',
 'old_request_source_fields':list(json.loads(prompts[0].split('\n',1)[1].split('\n上次已知格式错误：')[0])),
 'source_blocks':len(original['blocks']),'source_original_text_characters':len(original['original_text']),
 'original_text_also_repeated_in_blocks':len(''.join(b['text'] for b in original['blocks'])),
 'provider_parameter_form_observed':'Saved JSON request used top-level max_tokens and response_format.type=json_object; real usage and finish_reason received. Full provider documentation/maximum and raw HTTP headers not queried or independently verified.',
 'old_fallback_covered_blocks':len({b for s in a.fallback(original,['output_incomplete'])['sections'] for b in s['source_block_ids']}),
 'specific_remaining_output_token_need':'Cannot infer exact complete-token requirement from two partial outputs; both were incomplete at AS014, leaving later source regions uncovered.'}
result={'type':'zero_call_saved_material_protocol_replay','not_real_model_generation':True,'samples':[]}
work=D/'probe-work'/platform.system().lower();work.mkdir(parents=True,exist_ok=False)
for label in ('ranking01','review02'):
 base=work/label;w=base/'writer';w.mkdir(parents=True)
 if label=='ranking01':
  source=history/'article';shutil.copytree(source/'research',base/'research')
  for name in ('knowledge.json','product.json','writing_job.json'):shutil.copy2(source/'writer'/name,w/name)
 else:
  source=read(D/'fixtures/review02-article_structure.json')['source']
  for name in ('knowledge','product'):shutil.copy2(D/f'fixtures/review02-{name}.json',w/(name+'.json'))
 data=a.source_input(w,read(w/'knowledge.json')) if label=='ranking01' else source
 client=LocalProtocolClient()
 if label=='ranking01':structure=a.analyze(client,w,w,read(w/'knowledge.json'),{'offline_replay':True})
 else:
  from unittest.mock import patch
  with patch.object(a,'source_input',return_value=data):structure=a.analyze(client,w,w,read(w/'knowledge.json'),{'offline_replay':True})
 c=compiler.compile_article(read(w/'knowledge.json'),read(w/'product.json'))
 if label=='ranking01':bound=a.bind(c,structure);view=a.writer_view(structure)
 else:
  from unittest.mock import patch
  with patch.object(a,'source_input',return_value=data):bound=a.bind(c,structure);view=a.writer_view(structure)
 plan=p.plan(data);assert structure['status']=='structure_ready'
 roster=[{'id':s['id'],'subject':s['subject'],'claim_ids':s['claim_ids'],'structure_id':s['structure_id'],'binding':s['structure_binding']} for s in bound['sections']]
 assert [(s['subject'],s['claim_ids']) for s in bound['sections']]==[(s['subject'],s['claim_ids']) for s in c['sections']]
 own=next(s for s in bound['sections'] if s['subject']==read(w/'product.json')['name']);assert own['structure_id']==next(s['id'] for s in structure['sections'] if s['role']=='subject')
 row={'sample':label,'actual_source_sha256':p.digest(data),'status':structure['status'],'simulated_calls':len(client.calls),'primary_chunks':len(plan['chunks']),
  'source_block_count':len(data['blocks']),'merged_source_block_count':sum(len(s['source_block_ids']) for s in structure['sections']),
  'source_product_regions':sum(s['role']=='subject' for s in structure['sections']),'all_product_slots':roster,'owned_product_bound_to_first_subject':True,
  'all_claim_permissions_unchanged':True,'source_regions':[{'id':s['id'],'role':s['role'],'after':s['after'],'anchors':s['anchors'],'subsection_anchors':s['subsection_anchors']} for s in structure['sections']],
  'phase_max_calls_including_all_recoveries':plan['max_calls'],'phase_max_output_tokens':plan['max_output_tokens'],'phase_reservation_upper_cny':plan['reservation_upper_cny'],
  'initial_calls':len(plan['chunks']),'initial_output_tokens':sum(c['max_tokens'] for c in plan['calls'] if c['mode']=='compact'),
  'initial_reservation_upper_cny':sum(c['reservation_upper_cny'] for c in plan['calls'] if c['mode']=='compact'),
  'per_call_plan':[{k:c[k] for k in ('key','mode','input_bytes','max_tokens','reservation_upper_cny')} for c in plan['calls']]}
 if label=='ranking01':
  from geo_source_cards import consumer_prompts,article_logic,review_arbitration
  (w/'writer_done.json').write_text(json.dumps({'compilation':bound},ensure_ascii=False),encoding='utf8')
  # A labelled sizing surrogate only, never an article/model-quality result.
  (w/'draft.md').write_text('# 费用测算占位\n\n'+'界'*5950+'\n',encoding='utf8')
  fact=consumer_prompts.build('review',w);logic=article_logic.prompt(article_logic.build_input(w));arbitration=review_arbitration.context(w,{'failures':[]})
  assert all(value['original_article_source']==data for value in (json.loads(fact.split('资料：')[-1]),json.loads(logic.split('资料：')[-1]),arbitration))
  row['review_raw_source_preserved']=True
  row['review_sizing_surrogate_not_article']={'fact_input_bytes':p.request_bound(fact,1800)['input_bytes'] if False else len(json.dumps(request_payload(fact,1800)['messages'],ensure_ascii=False).encode('utf8'))+256,
   'logic_input_bytes':len(json.dumps(request_payload(logic,2400)['messages'],ensure_ascii=False).encode('utf8'))+256}
  assert row['review_sizing_surrogate_not_article']['fact_input_bytes']<=167936
  assert row['review_sizing_surrogate_not_article']['logic_input_bytes']<=131072
 result['samples'].append(row)
 (base/'bound.json').write_text(json.dumps(bound,ensure_ascii=False,indent=2),encoding='utf8')
old_first=read(history/'preflight.json');remaining_first_stage=sum(v for k,v in old_first['stage1_pending'].items() if k!='structure')
budget={'type':'offline_budget_envelope_not_authorization','prices':{'input_miss_per_million':2,'output_per_million':8,'source':'unchanged existing api_budget.py'},
 'no_discount_assumed':True,'global_limits':{'max_calls':p.MAX_STAGE_CALLS,'max_output_tokens_per_call':p.MAX_OUTPUT_TOKENS,'max_stage_output_tokens':p.MAX_STAGE_CALLS*p.MAX_OUTPUT_TOKENS,'max_input_bytes_per_call':p.MAX_INPUT_BYTES},
 'rank01':result['samples'][0],'inherited_other_first_stage_upper_cny':remaining_first_stage,
 'rank01_first_stage_with_all_structure_recovery_upper_cny':remaining_first_stage+result['samples'][0]['phase_reservation_upper_cny'],
 'historical_real_spend_unchanged_cny':.0200742,'remaining_incremental_authorization_cny':7.1799258,
 'caveats':['No provider balance/current budget availability query; arithmetic only, not authorization or executed reservation.',
 'Writer/fact/logic retain previous conditional byte envelopes and require current-input remeasurement before a future real run.',
 'Arbitration and content repair are excluded from first stage; all actual arbitration batches require a separate complete preflight.',
 'Old v2 acceptance runner does not install this new phase plan; any future real runner must consume plan.calls/max_tokens before sending.'],
 'api_calls':0,'budget_mutations':0}
logs=D/'logs';logs.mkdir(exist_ok=True)
for name,value in [('historical-root-cause',audit),('saved-source-replay',result),('budget-plan',budget)]:
 (logs/(name+'-'+platform.system().lower()+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
assert not offline_guard.blocked
print(json.dumps({'platform':platform.system(),'replay_samples':len(result['samples']),'all_anchors_preserved':True,'rank01_initial_calls':result['samples'][0]['initial_calls'],
 'rank01_max_calls':result['samples'][0]['phase_max_calls_including_all_recoveries'],'rank01_structure_upper_cny':result['samples'][0]['phase_reservation_upper_cny'],
 'rank01_first_stage_conditional_upper_cny':budget['rank01_first_stage_with_all_structure_recovery_upper_cny'],'network_attempts':len(offline_guard.blocked),'real_api_calls':0}))

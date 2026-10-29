"""Offline protocol/fault tests. Simulated structures are not model verdicts."""
import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards import structure_protocol as p,structure_analyzer as a
from geo_source_cards.deepseek_api import APIError,DeepSeekClient,request_payload
from geo_source_cards.runtime import atomic_json
from geo_source_cards.article_compiler import compile_article,prepare
from tests.test_article_compiler import case

ROOT=Path(os.environ['GEO_STRUCTURE_FIXTURES'])
read=lambda path:json.loads(Path(path).read_text('utf8'))
def actual():return read(ROOT/'history/rank01/article_structure.json')['source']
def synthetic(n=7):
 blocks=[{'id':'O0001','kind':'heading','text':'选购问题与比较标准'}]
 for i in range(n):
  blocks.extend([{'id':'','kind':'heading','text':f'{i+1}. 对象{i}设备'},
                 {'id':'','kind':'paragraph','text':'这部分记录组成与规格。'},
                 {'id':'','kind':'heading','text':'怎么理解组成？'},
                 {'id':'','kind':'paragraph','text':'这部分仍介绍同一对象。'}])
 blocks.append({'id':'','kind':'heading','text':'结尾总结'})
 for i,b in enumerate(blocks,1):b['id']=f'O{i:04d}'
 return {'original_title':'设备选购比较','original_url':'https://example.test/source','original_text':'\n'.join(b['text'] for b in blocks),'blocks':blocks,'requirements':{'genre':'ranking'}}
def response(sent):
 return {'article_topic':'可用资料的组织方式','article_purpose':'以同一问题组织已有资料','genre':sent['expected_genre'],
  'sections':[{'section_id':g['section_id'],'role':g['role_hint'],'role_status':'inferred','topic':'说明当前部分','purpose':'解释前提并承接下文',
    'moves':['explain','qualify'],'after':g['after'],'anchors':g['anchors']} for g in sent['units']]}

class LocalProtocolClient:
 def __init__(self,fault=None,budget=None):self.calls=[];self.fault=fault;self.budget=budget
 def complete(self,message,folder,*,max_tokens,stage,meta):
  sent=json.loads(message.split('资料：')[-1]);self.calls.append((message,str(folder),max_tokens));folder.mkdir(parents=True,exist_ok=True)
  payload=request_payload(message,max_tokens);atomic_json(folder/'request.json',payload)
  value=response(sent)
  if self.fault:
   result=self.fault(sent,folder,value)
   if isinstance(result,BaseException):raise result
   if result is not None:value=result
  atomic_json(folder/'response.json',value);atomic_json(folder/'answer.json',{'content':json.dumps(value,ensure_ascii=False),'finish_reason':'stop'})
  atomic_json(folder/'api_state.json',{'state':'RESPONDED','payload_sha256':p.digest(payload)})
  return value

class StructureRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name);self.data=synthetic()
 def run_analyzer(self,c=None,data=None):
  with patch.object(a,'source_input',return_value=data or self.data):return a.analyze(c or LocalProtocolClient(),self.root,self.root,{}, {'sample':'offline'})
 def test_historical_truncations_rejected_by_actual_api_response_parser(self):
  for i in range(2):
   historical=read(ROOT/f'history/rank01/article/writer/structure_calls/attempt-{i}/answer.json')
   class Result:
    status_code=200
    def json(self):return {'choices':[{'finish_reason':historical['finish_reason'],'message':{'content':historical['content']}}],'usage':historical['usage']}
   class Session:
    calls=0
    def post(self,*args,**kwargs):self.calls+=1;return Result()
   key=self.root/'test.key';key.write_text('sk-'+('offline' * 6),encoding='utf8');session=Session();c=DeepSeekClient(key,session=session)
   folder=self.root/f'history-{i}'
   with self.assertRaisesRegex(APIError,'output_incomplete'):c.complete('offline replay of saved response',folder,max_tokens=2400)
   self.assertEqual(session.calls,1);self.assertEqual(read(folder/'api_state.json')['state'],'INVALID_RESPONSE');self.assertFalse((folder/'response.json').exists())
 def test_saved_rank01_source_all_84_anchors_and_10_products_are_covered(self):
  data=actual();plan=p.plan(data);groups=plan['units'];products=[g for g in groups if g['role_hint']=='subject']
  self.assertEqual(len(data['blocks']),84);self.assertEqual(len(products),10)
  self.assertEqual([b['id'] for g in groups for b in g['blocks']],[b['id'] for b in data['blocks']])
  first=products[0];self.assertEqual(first['anchors'],['O0003','O0033']);self.assertTrue({'O0008','O0011','O0031'}<=set(first['subsection_anchors']))
  out=self.run_analyzer(data=data);self.assertEqual(out['status'],'structure_ready');self.assertEqual(len(out['sections']),len(groups));self.assertNotIn('source',out)
 def test_saved_review02_source_retains_every_discovered_product(self):
  data=read(ROOT/'fixtures/review02-article_structure.json')['source'];plan=p.plan(data);out=self.run_analyzer(data=data)
  self.assertEqual(sum(s['role']=='subject' for s in out['sections']),10);self.assertEqual([s['id'] for s in out['sections']],[g['section_id'] for g in plan['units']])
 def test_compact_schema_and_full_research_not_duplicated_in_prompt(self):
  data=actual();plan=p.plan(data)
  for c in plan['calls']:
   message=p.prompt(data,c['units'],c['mode']);sent=json.loads(message.split('资料：')[-1]);self.assertEqual(message.count('"schema"'),1)
   self.assertNotIn('original_text',sent);self.assertNotIn('source_quote',message);self.assertNotIn('claim_ledger',message)
   self.assertEqual(c['max_tokens'],p.output_limit(c['units'],c['mode']));self.assertLessEqual(c['max_tokens'],p.MAX_OUTPUT_TOKENS)
  self.assertEqual([b for g in plan['units'] for b in g['blocks']],data['blocks'])
 def test_split_merge_order_and_stable_section_ids(self):
  self.data=synthetic(12);plan=p.plan(self.data);out=self.run_analyzer();self.assertGreater(len(plan['chunks']),1)
  self.assertEqual([s['id'] for s in out['sections']],[g['section_id'] for g in plan['units']]);self.assertEqual([b for s in out['sections'] for b in s['source_block_ids']],[b['id'] for b in self.data['blocks']])
 def test_product_subheadings_do_not_split_same_product(self):
  plan=p.plan(self.data);products=[g for g in plan['units'] if g['role_hint']=='subject'];self.assertEqual(len(products),7)
  self.assertTrue(all(len(g['blocks'])==4 for g in products));self.assertTrue(all(g['subsection_anchors'] for g in products))
 def test_single_large_product_not_cut_to_force_input_budget(self):
  self.data['blocks'][2]['text']='证据段落。'*10000;c=LocalProtocolClient();out=self.run_analyzer(c)
  self.assertEqual(out['status'],'structure_incomplete');self.assertEqual(c.calls,[]);self.assertIn('ceiling',out['reason'])
 def test_missing_anchor_is_explicit_pending_without_request(self):
  self.data['blocks'][1].pop('id');c=LocalProtocolClient();out=self.run_analyzer(c);self.assertEqual(c.calls,[])
  self.assertEqual(out['status'],'structure_incomplete');self.assertIn('needs_check',out['reason'])
 def test_duplicate_anchor_rejected(self):
  self.data['blocks'][1]['id']='O0001';self.assertEqual(self.run_analyzer()['status'],'structure_incomplete')
 def test_schema_missing_extra_empty_duplicate_and_reordered_sections_rejected(self):
  data=actual();plan=p.plan(data);c=plan['calls'][0];good=response(json.loads(p.prompt(data,c['units'],c['mode']).split('资料：')[-1]))
  changes=[lambda v:v.pop('article_purpose'),lambda v:v.update(extra='unexpected'),lambda v:v.update(sections=[]),lambda v:v['sections'].reverse(),lambda v:v['sections'][1].update(section_id=v['sections'][0]['section_id']),lambda v:v['sections'][0].pop('moves'),lambda v:v['sections'][0].update(anchors=['O9999']),lambda v:v['sections'][0].update(after='future'),lambda v:v['sections'][0].update(topic='过长'*100)]
  for change in changes:
   value=copy.deepcopy(good);change(value)
   with self.assertRaises((ValueError,KeyError)):p.validate_chunk(value,data,c['units'],c['mode'])
 def test_length_recovers_by_smaller_different_protocol_not_repeat(self):
  def fault(sent,folder,value):
   if sent['mode']=='compact':
    atomic_json(folder/'answer.json',{'content':'{"sections":[','finish_reason':'length'});return APIError('output_incomplete')
  c=LocalProtocolClient(fault);out=self.run_analyzer(c);self.assertEqual(out['status'],'structure_ready')
  primary=[m for m,path,t in c.calls if path.endswith('/primary') or path.endswith('\\primary')];minimal=[m for m,path,t in c.calls if not path.endswith('primary')]
  self.assertTrue(primary and minimal);self.assertTrue(all(m not in primary for m in minimal));self.assertTrue(all(len(json.loads(m.split('资料：')[-1])['units'])==1 for m in minimal))
 def test_malformed_json_response_recovers_with_bounded_protocol(self):
  def fault(sent,folder,value):return APIError('invalid_response') if sent['mode']=='compact' else None
  c=LocalProtocolClient(fault);self.assertEqual(self.run_analyzer(c)['status'],'structure_ready');self.assertLessEqual(len(c.calls),p.plan(self.data)['max_calls'])
 def test_one_failed_region_cannot_mark_incomplete_contract_ready(self):
  c=LocalProtocolClient(lambda *_:{});out=self.run_analyzer(c);self.assertEqual(out['status'],'structure_incomplete');self.assertTrue(out['degraded'])
  with self.assertRaises(p.StructureIncomplete):p.verify(out,self.data)
  before=len(c.calls);self.assertEqual(self.run_analyzer(c),out);self.assertEqual(len(c.calls),before)
 def test_ambiguous_product_role_cannot_become_binding_or_silent_omission(self):
  def fault(sent,folder,value):
   for s in value['sections']:
    if s['role']=='subject':s.update(role='unknown',role_status='needs_check')
   return value
  out=self.run_analyzer(LocalProtocolClient(fault));self.assertEqual(out['status'],'structure_incomplete')
 def test_opening_cannot_be_own_product(self):
  data=actual();c=p.plan(data)['calls'][0];v=response(json.loads(p.prompt(data,c['units'],c['mode']).split('资料：')[-1]));v['sections'][0]['role']='subject'
  with self.assertRaises(ValueError):p.validate_chunk(v,data,c['units'],c['mode'])
 def test_completed_contract_resume_uses_zero_additional_calls(self):
  c=LocalProtocolClient();out=self.run_analyzer(c);before=len(c.calls);self.assertEqual(out,self.run_analyzer(c));self.assertEqual(len(c.calls),before)
 def test_saved_chunks_resume_after_interrupt_without_regeneration(self):
  class Interrupted(BaseException):pass
  def fault(sent,folder,value):
   if 'chunk-001' in str(folder):raise Interrupted()
  c=LocalProtocolClient(fault)
  with self.assertRaises(Interrupted):self.run_analyzer(c)
  # Simulate a process crash AFTER durable provider response was saved.
  plan=p.plan(self.data);call=next(c for c in plan['calls'] if c['key']=='chunk-001/primary');folder=self.root/'structure_calls/compact-v2'/call['key']
  LocalProtocolClient().complete(p.prompt(self.data,call['units'],call['mode']),folder,max_tokens=call['max_tokens'],stage='writer',meta={})
  resumed=LocalProtocolClient();out=self.run_analyzer(resumed);self.assertEqual(out['status'],'structure_ready')
  self.assertFalse(any('chunk-000' in path or 'chunk-001' in path for _,path,_ in resumed.calls))
 def test_changed_source_invalidates_completed_chunks_without_call(self):
  c=LocalProtocolClient();self.run_analyzer(c);before=len(c.calls);self.data['blocks'][2]['text']+='资料改变'
  with self.assertRaises(p.StructureIncomplete):self.run_analyzer(c)
  self.assertEqual(len(c.calls),before);self.assertEqual(read(self.root/'structure_calls/compact-v2/status.json')['status'],'needs_reanalysis')
 def test_unknown_request_never_retried_even_on_resume(self):
  c=LocalProtocolClient(lambda *_:APIError('network_delivery_unknown',uncertain=True))
  for _ in range(2):
   with self.assertRaises(APIError) as raised:self.run_analyzer(c)
   self.assertTrue(raised.exception.uncertain)
  self.assertEqual(len(c.calls),1)
 def test_insufficient_full_stage_budget_stops_before_first_request(self):
  class Budget:
   def remaining(self,*_):return p.plan(actual())['calls'][0]['reservation_upper_cny']
  c=LocalProtocolClient(budget=Budget())
  with self.assertRaisesRegex(APIError,'structure_budget_exceeded'):self.run_analyzer(c,data=actual())
  self.assertEqual(c.calls,[])
 def test_legacy_exhausted_execution_cannot_be_reset_by_new_protocol(self):
  atomic_json(self.root/'structure_calls/attempt-0/api_state.json',{'state':'INVALID_RESPONSE','failure_code':'output_incomplete'});c=LocalProtocolClient()
  with self.assertRaises(p.StructureIncomplete):self.run_analyzer(c)
  self.assertEqual(c.calls,[])
 def test_tampered_chunk_hash_cannot_resume_as_valid(self):
  class Interrupted(BaseException):pass
  c=LocalProtocolClient(lambda s,f,v:Interrupted() if 'chunk-001' in str(f) else None)
  with self.assertRaises(Interrupted):self.run_analyzer(c)
  accepted=next(self.root.rglob('accepted.json'));value=read(accepted);value['result']['article_topic']='篡改';atomic_json(accepted,value)
  # Clear only the simulator's unsent interruption marker, in disposable fixture.
  attempt=self.root/'structure_calls/compact-v2/chunk-001/primary/attempt_status.json';atomic_json(attempt,{'status':'known_failure'})
  resumed=LocalProtocolClient();out=self.run_analyzer(resumed);self.assertEqual(out['status'],'structure_incomplete');self.assertEqual(resumed.calls,[])
 def test_compiler_binding_preserves_owned_identity_and_claim_permissions(self):
  data=actual();out=self.run_analyzer(data=data);history=ROOT/'history/rank01/article/writer';k,pd=read(history/'knowledge.json'),read(history/'product.json')
  with patch.object(a,'source_input',return_value=data):
   atomic_json(self.root/'knowledge.json',k);baseline=compile_article(k,pd);bound=a.bind(baseline,out)
   own=next(s for s in bound['sections'] if s['subject']==pd['name']);first=next(s for s in out['sections'] if s['role']=='subject')
   self.assertEqual(own['structure_id'],first['id']);self.assertEqual([(s['subject'],s['claim_ids']) for s in baseline['sections']],[(s['subject'],s['claim_ids']) for s in bound['sections']])
   view=json.dumps(a.writer_view(out),ensure_ascii=False)
   for forbidden in ('露卡菲娅','9.98','84.2%','20264227'):self.assertNotIn(forbidden,view)
   self.assertIn('source_predecessor',view)
 def test_incomplete_structure_blocks_compiler_and_direct_writer(self):
  from geo_source_cards import section_writer
  k,pd=case();atomic_json(self.root/'knowledge.json',k);atomic_json(self.root/'product.json',pd);atomic_json(self.root/'compilation.json',compile_article(k,pd))
  self.run_analyzer(LocalProtocolClient(lambda *_:{}))
  with patch.object(a,'source_input',return_value=self.data):
   with self.assertRaises(p.StructureIncomplete):prepare(self.root)
   c=LocalProtocolClient()
   with self.assertRaises(p.StructureIncomplete):section_writer.generate(c,self.root,{})
   self.assertEqual(c.calls,[])
 def test_global_stage_call_and_output_caps_enforced(self):
  plan=p.plan(actual());self.assertLessEqual(plan['max_calls'],p.MAX_STAGE_CALLS);self.assertEqual(plan['max_calls'],len(plan['calls']))
  self.assertEqual(plan['max_output_tokens'],sum(c['max_tokens'] for c in plan['calls']))
  with self.assertRaises(p.StructureIncomplete):p.plan(synthetic(30))
 def test_stage_envelope_matches_real_budget_reserve_formula(self):
  from geo_source_cards.api_budget import Budget
  from geo_source_cards.pipeline_control import save_settings
  plan=p.plan(actual());budget=Budget(self.root/'budget');self.addCleanup(budget.close)
  save_settings(budget.root,{'article_budget_cny':8,'daily_budget_cny':10})
  for i,c in enumerate(plan['calls']):
   payload=request_payload(p.prompt(actual(),c['units'],c['mode']),c['max_tokens'])
   identity=budget.reserve(payload,budget.root/f'call-{i}',{'date':'2026-10-23','category':'排行类','number':1},'writer')
   row=budget.db.execute('select reserved from costs where id=?',(identity,)).fetchone()
   self.assertAlmostEqual(row['reserved'],c['reservation_upper_cny'])
 def test_chunk_unknown_state_without_local_marker_still_blocks_all_sends(self):
  plan=p.plan(self.data);self.root.joinpath('structure_calls/compact-v2').mkdir(parents=True)
  # Initialize this new protocol's immutable input marker using a budget stop.
  class Budget:
   def remaining(self,*_):return 0
  with self.assertRaises(APIError):self.run_analyzer(LocalProtocolClient(budget=Budget()))
  folder=self.root/'structure_calls/compact-v2/chunk-001/primary'
  atomic_json(folder/'api_state.json',{'state':'REQUEST_UNKNOWN'});c=LocalProtocolClient()
  with self.assertRaises(APIError) as raised:self.run_analyzer(c)
  self.assertTrue(raised.exception.uncertain);self.assertEqual(c.calls,[])
 def test_generation_lock_blocks_concurrent_analysis_without_calls(self):
  from geo_source_cards.runtime import process_lock
  c=LocalProtocolClient()
  with process_lock(self.root/'structure_calls/compact-v2/analysis.lock'):
   with self.assertRaises(RuntimeError):self.run_analyzer(c)
  self.assertEqual(c.calls,[])
 def test_changed_contract_source_is_rejected_by_writer_view(self):
  data=actual();out=self.run_analyzer(data=data);atomic_json(self.root/'knowledge.json',{})
  altered=copy.deepcopy(data);altered['blocks'][3]['text']+='新来源'
  with patch.object(a,'source_input',return_value=altered):
   with self.assertRaisesRegex(ValueError,'Stale compact'):a.writer_view(out)
 def test_received_response_crash_resume_does_not_double_reserve_paid_chunk(self):
  self.test_saved_chunks_resume_after_interrupt_without_regeneration()
  # All accepted files are immutable valid chunks; remove only final publication
  # to simulate a crash before the final atomic structure write.
  (self.root/'article_structure.json').unlink()
  class Budget:
   def remaining(self,*_):return 0
  c=LocalProtocolClient(budget=Budget());out=self.run_analyzer(c)
  self.assertEqual(out['status'],'structure_ready');self.assertEqual(c.calls,[])
 def test_all_completed_chunks_validate_before_sending_earlier_missing_chunk(self):
  c=LocalProtocolClient();self.run_analyzer(c);(self.root/'article_structure.json').unlink()
  accepted=sorted(self.root.rglob('accepted.json'));last=read(accepted[-1]);last['result']['article_topic']='被改动';atomic_json(accepted[-1],last)
  # Remove one earlier accepted result and its provider response in a disposable
  # test copy; later corrupted evidence must still stop before any new request.
  early=accepted[0].parent
  for name in ('accepted.json','response.json','answer.json','api_state.json','attempt_status.json'):(early/name).unlink()
  resumed=LocalProtocolClient();out=self.run_analyzer(resumed)
  self.assertEqual(out['status'],'structure_incomplete');self.assertEqual(resumed.calls,[])
 def test_compact_contract_keeps_complete_raw_original_in_all_reviewer_inputs(self):
  from geo_source_cards import consumer_prompts,article_logic,review_arbitration
  data=actual();out=self.run_analyzer(data=data);k,pd=case()
  for name,value in [('knowledge.json',k),('product.json',pd)]:atomic_json(self.root/name,value)
  with patch.object(a,'source_input',return_value=data):
   c=a.bind(compile_article(k,pd),out);atomic_json(self.root/'writer_done.json',{'compilation':c})
   (self.root/'draft.md').write_text('# 资料比较\n\n可以根据自己的需求比较。\n\n## 比较条件\n\n按照相同条件选择。\n',encoding='utf8')
   fact=json.loads(consumer_prompts.build('review',self.root).split('资料：')[-1])
   logic=json.loads(article_logic.prompt(article_logic.build_input(self.root)).split('资料：')[-1])
   arbitration=review_arbitration.context(self.root,{'failures':[]})
  for value in (fact,logic,arbitration):self.assertEqual(value['original_article_source'],data)
  self.assertNotIn('source',out);self.assertEqual(len(fact['original_article_source']['blocks']),84)
 def test_raw_source_read_for_review_rejects_stale_structure(self):
  data=actual();out=self.run_analyzer(data=data);atomic_json(self.root/'knowledge.json',{})
  altered=copy.deepcopy(data);altered['blocks'][-1]['text']+='修正来源'
  with patch.object(a,'source_input',return_value=altered):
   with self.assertRaisesRegex(ValueError,'Stale compact'):a.review_source(out)

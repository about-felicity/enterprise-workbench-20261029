import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards import structure_analyzer as a,section_writer as w,review_arbitration as r,quality_checks as q
from geo_source_cards.article_compiler import compile_article,validate_document,writer_view
from geo_source_cards.deepseek_api import APIError
from geo_source_cards.runtime import atomic_json
from geo_source_cards.article_logic import text_hash,segments
from tests.test_article_compiler import case

class AnalyzerTests(unittest.TestCase):
 def data(self):return {'original_url':'https://example.test/a','original_title':'如何比较信息','original_text':'先提出问题。\n\n再解释标准。','blocks':[{'id':'O0001','kind':'paragraph','text':'先提出问题。'},{'id':'O0002','kind':'paragraph','text':'再解释标准。'}],'requirements':{'genre':'review'}}
 def test_actual_paragraph_fallback_and_structure_binding(self):
  data=self.data();value=a.fallback(data,['invalid_response']);self.assertEqual([s['source_quote'] for s in value['sections']],['先提出问题。','再解释标准。'])
  value.update(version=a.VERSION,source=data,input_sha256='input');value['sha256']=a.digest(value)
  k,p=case();bound=a.bind(compile_article(k,p),value)
  self.assertEqual(bound['sections'][0]['structure_task']['argument_step'],value['sections'][0]['argument_step'])
  task=w.plan(bound,{'min_body_hanzi':100,'min_lead_hanzi':20})[1];self.assertIn(value['sections'][0]['purpose'],task['purpose']);self.assertTrue(set(value['sections'][0]['required_content'])<=set(task['required_content']))
  self.assertEqual(len(writer_view(bound)['structure']['sections']),len(value['sections']));self.assertNotIn('source_quote',writer_view(bound)['structure']['sections'][0])
  value['sections'][0]['source_quote']='来源没有这句话'
  with self.assertRaises(ValueError):a.validate(value,data)
 def test_bounded_bad_json_falls_back_then_resume_does_not_send(self):
  class Client:
   calls=0
   def complete(self,*args,**kwargs):self.calls+=1;return {}
  with tempfile.TemporaryDirectory() as tmp,patch.object(a,'source_input',return_value=self.data()):
   c=Client();out=a.analyze(c,Path(tmp),Path(tmp),{},{});self.assertTrue(out['degraded']);self.assertEqual(c.calls,2)
   self.assertEqual(a.analyze(c,Path(tmp),Path(tmp),{},{}),out);self.assertEqual(c.calls,2)
 def test_unknown_analyzer_request_never_falls_back_or_retries(self):
  class Client:
   calls=0
   def complete(self,*args,**kwargs):self.calls+=1;raise APIError('request_unknown',uncertain=True)
  with tempfile.TemporaryDirectory() as tmp,patch.object(a,'source_input',return_value=self.data()):
   c=Client()
   with self.assertRaises(APIError):a.analyze(c,Path(tmp),Path(tmp),{},{} )
   self.assertEqual(c.calls,1);self.assertFalse((Path(tmp)/'article_structure.json').exists())
 def test_real_fetched_original_selected_not_first_unrelated_source(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);atomic_json(root/'research_input.json',{'observations':[{'sources':[{'url':'wrong','article':{'status':'fetched','text':'错误来源'}},{'url':'right','article':{'status':'fetched','title':'真实标题','text':'真实内容','paragraphs':[{'kind':'heading','text':'真实章节'}]}}]}]})
   with patch('geo_source_cards.staged_editorial.research_for_writer',return_value=root):d=a.source_input(root,{'reference_design':{'primary_url':'right'}})
   self.assertEqual(d['blocks'][0]['text'],'真实章节');self.assertEqual(d['original_text'],'真实内容')

class StructureRevisionTests(unittest.TestCase):
 def test_repair_carries_original_structure_into_new_compilation(self):
  from geo_source_cards.article_compiler import prepare
  k,p=case();data=AnalyzerTests().data();structure=a.fallback(data,['known format error']);structure.update(version=a.VERSION,source=data,input_sha256='input');structure['sha256']=a.digest(structure);compiled=a.bind(compile_article(k,p),structure)
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.consumer_prompts.evidence_units',return_value=[]):
   root=Path(tmp);atomic_json(root/'knowledge.json',k);atomic_json(root/'product.json',p);atomic_json(root/'paragraph_repair.json',{'compiled_contract':compiled})
   repaired=prepare(root);self.assertEqual(repaired['article_structure'],structure);self.assertEqual(repaired['sha256'],compiled['sha256'])
 def test_final_audit_is_invalidated_by_knowledge_change_or_missing_logic(self):
  from geo_source_cards.review_quality import verify_final
  k,p=case();text='正文';answer={'quality_pipeline':{'version':'review-quality-v1','draft_sha256':text_hash(text),'evidence_sha256':a.digest({'knowledge':k,'product':p}),'independent_logic_executed':True}}
  verify_final(answer,text,k,p)
  changed=copy.deepcopy(k);changed['knowledge_units'][0]['content']='改变材料'
  for body,knowledge in ((text+'修改',k),(text,changed)):
   with self.assertRaises(ValueError):verify_final(answer,body,knowledge,p)
  answer['quality_pipeline']['independent_logic_executed']=False
  with self.assertRaises(ValueError):verify_final(answer,text,k,p)

class SectionTests(unittest.TestCase):
 def setup_root(self,path):
  k,p=case();c=compile_article(k,p)
  for n,v in [('knowledge.json',k),('product.json',p),('compilation.json',c)]:atomic_json(path/n,v)
  return c
 def client(self,fail=None):
  class Client:
   calls=[]
   def __init__(self):self.calls=[]
   def complete(self,prompt,folder,**kwargs):
    data=json.loads(prompt.split('资料：')[-1]);t=data['task'];self.calls.append((t['id'],folder.name));folder.mkdir(parents=True,exist_ok=True)
    if fail:
     outcome=fail(t,folder)
     if outcome is not None:return outcome
    text=t['id']+'本节围绕读者的问题展开说明。'*(t['target_hanzi']//10+2)
    result={'id':t['id'],'title':'产品比较','heading':t['topic'],'paragraphs':[{'text':text,'statement_type':'general_advice','claim_ids':[]}]}
    atomic_json(folder/'response.json',result);return result
  return Client()
 def test_missing_section_retries_only_that_section_then_resume_zero_calls(self):
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':300,'min_lead_hanzi':20}):
   root=Path(tmp);c=self.setup_root(root);client=self.client(lambda t,f: {'id':t['id'],'paragraphs':[]} if t['id']=='S2' and f.name=='attempt-0' else None)
   out=w.generate(client,root,{});validate_document(out,c,complete=True)
   self.assertEqual([x[0] for x in client.calls].count('S2'),2);calls=len(client.calls)
   self.assertEqual(w.generate(client,root,{}),out);self.assertEqual(len(client.calls),calls)
   state=json.loads((root/'section_calls/manifest.json').read_text());self.assertEqual(state['status'],'complete')
 def test_known_parse_truncation_and_rate_limit_recover_but_timeout_unknown_does_not(self):
  for code in ('invalid_response','output_incomplete','http_429'):
   def failure(t,f):
    if t['id']=='S1' and f.name=='attempt-0':raise APIError(code)
   with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
    root=Path(tmp);self.setup_root(root);client=self.client(failure);w.generate(client,root,{})
    self.assertEqual([x[0] for x in client.calls].count('S1'),2)
  def unknown(t,f):
   if t['id']=='S2':raise APIError('request_unknown',uncertain=True)
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
   root=Path(tmp);self.setup_root(root);client=self.client(unknown)
   with self.assertRaises(APIError):w.generate(client,root,{})
   self.assertEqual([x[0] for x in client.calls].count('S2'),1);self.assertTrue((root/'section_calls/S1/accepted.json').is_file());self.assertFalse((root/'section_calls/assembled.json').exists())
 def test_persistent_bad_format_exhausts_without_delivery(self):
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
   root=Path(tmp);self.setup_root(root);client=self.client(lambda t,f:{})
   with self.assertRaisesRegex(APIError,'section_generation_exhausted'):w.generate(client,root,{})
   self.assertEqual(len(client.calls),3);self.assertFalse((root/'section_calls/assembled.json').exists())
 def test_empty_missing_reordered_duplicate_and_truncated_body_rejected(self):
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
   root=Path(tmp);c=self.setup_root(root);out=w.generate(self.client(),root,{})
   mutations=[lambda d:d.update(sections=[]),lambda d:d['sections'].pop(),lambda d:d['sections'].reverse(),lambda d:d['sections'][0].update(paragraphs=[]),lambda d:d['sections'][1]['paragraphs'][0].update(text=d['sections'][0]['paragraphs'][0]['text']),lambda d:d['sections'][0]['paragraphs'][0].update(text='[未完]')]
   for mutate in mutations:
    bad=copy.deepcopy(out);mutate(bad['document'])
    with self.assertRaises(ValueError):validate_document(bad,c,complete=True)
 def test_saved_component_hash_and_changed_task_rejected(self):
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
   root=Path(tmp);self.setup_root(root);client=self.client();w.generate(client,root,{})
   with self.assertRaisesRegex(ValueError,'input/version'):w.generate(client,root,{'revision':1})
   atomic_json(root/'section_calls/S1/accepted.json',{})
   with self.assertRaisesRegex(ValueError,'Saved section'):w.generate(client,root,{})

class ExecutionProtectionTests(unittest.TestCase):
 def test_generation_lock_blocks_duplicate_task_and_budget_failure_is_terminal(self):
  from geo_source_cards.runtime import process_lock
  helper=SectionTests()
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
   root=Path(tmp);helper.setup_root(root);client=helper.client()
   with process_lock(root/'section_calls/generation.lock'):
    with self.assertRaises(RuntimeError):w.generate(client,root,{})
   self.assertEqual(client.calls,[])
   class BudgetClient:
    def complete(self,*args,**kwargs):raise APIError('article_budget_exceeded')
   with self.assertRaisesRegex(APIError,'article_budget_exceeded'):w.generate(BudgetClient(),root,{})
   state=json.loads((root/'section_calls/manifest.json').read_text());self.assertEqual(state['status'],'blocked');self.assertEqual(state['failure_code'],'article_budget_exceeded')
 def test_known_invalid_state_after_crash_is_not_misclassified_unknown(self):
  helper=SectionTests()
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
   root=Path(tmp);helper.setup_root(root);client=helper.client();atomic_json(root/'section_calls/S1/attempt-0/api_state.json',{'state':'INVALID_RESPONSE','failure_code':'output_incomplete'})
   out=w.generate(client,root,{});self.assertTrue(out['document']['sections']);self.assertNotIn(('S1','attempt-0'),client.calls);self.assertIn(('S1','attempt-1'),client.calls)

class ReviewCalibrationTests(unittest.TestCase):
 def test_c60_generic_inference_is_proposed_for_independent_review_c34_advice_is_not(self):
  for text in ('植萃组合和乳液质地说明清洁效果好。','产品的成分和质地与温和功效相符。'):
   self.assertTrue(q.semantic_candidates('# 主题\n\n'+text))
  for text in ('可以考虑小规格试用，旅行时根据行李选择。','成分和质地不能说明防脱效果。'):
   self.assertEqual(q.semantic_candidates('# 主题\n\n'+text),[])
 def test_count_11_vs_10_in_body_not_all_numbers_or_subsets(self):
  k,p=case();k['reference_design']['products']=[{'name':f'第{i}牌洗发水'} for i in range(10)]
  for text in ('本文介绍十款产品。','这十款按信息介绍。','本次对比10款。'):
   self.assertTrue(q.findings('# 产品比较\n\n'+text,k,p))
  for text in ('这十一款按信息介绍。','规格200ml，阅读10个步骤。','其中十款作为其他选择。','其余十款可继续比较。'):
   self.assertEqual(q.findings('# 产品比较\n\n'+text,k,p),[])
 def data(self):
  k,p=case();text='# 比较\n\n可以按行李需要考虑小规格试用。\n\n植萃质地说明清洁效果好。'
  return {'version':r.VERSION,'draft_sha256':text_hash(text),'evidence_sha256':r.digest({'knowledge':k,'product':p}),'paragraphs':segments(text),'knowledge':k,'product':p,'original_source_units':[],'proposals':[{'id':'ISS1','origin':'fact','kind':'unsupported_fact','reason':'试用缺实验','paragraph_ids':['P002']},{'id':'ISS2','origin':'semantic_candidate','kind':'unsupported_inference','reason':'成分推效果','paragraph_ids':['P003']}]},text
 def decisions(self):return [{'issue_id':'ISS1','classification':'general_advice','paragraph_ids':['P002'],'article_quote':'可以按行李需要考虑小规格试用。','source_ids':[],'source_quote':'','reason':'有条件的普通取舍，不是已证实属性','repair':''},{'issue_id':'ISS2','classification':'confirmed_error','paragraph_ids':['P003'],'article_quote':'植萃质地说明清洁效果好。','source_ids':[],'source_quote':'','reason':'成分与质地不能证明成品效果','repair':'删除效果推论，保留实际有依据的组成'}]
 def test_c34_c60_reviewer_subpass_and_hash_bound_route(self):
  data,text=self.data();answer={'failures':['C34','C60'],'checks':{'fact':True},'claims':[]};cert=r.validate({'decisions':self.decisions()},data);cert['source_review']=answer
  out=r.apply(answer,cert,data);r.enforce(out,text,data['knowledge'],data['product'])
  self.assertEqual(len(out['review_issues']),1);self.assertEqual(out['review_issues'][0]['paragraph_ids'],['P003'])
  with self.assertRaises(ValueError):r.enforce(out,text+'新版',data['knowledge'],data['product'])
 def test_uncertain_remains_disputed_false_checks_not_overridden(self):
  data,text=self.data();ds=self.decisions();ds[1].update(classification='needs_check',reason='资料不足不能确认')
  answer={'checks':{'fact':False},'failures':['旧意见'],'claims':[{'supported':False}]};cert=r.validate({'decisions':ds},data);out=r.apply(answer,cert,data)
  self.assertEqual(out['quality_status'],'ready_with_disputes');self.assertEqual(len(out['review_disputes']),1);self.assertFalse(out['checks']['fact']);self.assertFalse(out['claims'][0]['supported'])
 def test_invented_anchors_sources_missing_decisions_rejected(self):
  data,_=self.data()
  for mutate in (lambda d:d.pop(),lambda d:d[0].update(article_quote='不存在'),lambda d:d[0].update(source_ids=['PF999']),lambda d:d[0].update(source_quote='没有的资料'),lambda d:d[1].update(repair='')):
   ds=self.decisions();mutate(ds)
   with self.assertRaises(ValueError):r.validate({'decisions':ds},data)
 def test_deterministic_confirmed_count_cannot_be_waived(self):
  data,_=self.data();data['proposals'][0].update(origin='deterministic',repair='修正总数')
  out=r.apply({},r.validate({'decisions':self.decisions()},data),data)
  self.assertEqual(len(out['review_issues']),2)

class PipelineClosureTests(unittest.TestCase):
 def test_writer_reviewer_patch_and_fresh_review_operate_on_current_version(self):
  from geo_source_cards import review_quality,article_logic as logic,paragraph_repair,consumer_prompts
  from tests.test_article_logic import LogicTests
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.consumer_prompts.evidence_units',return_value=[]):
   base=Path(tmp);writer=base/'writer';review=base/'review';writer.mkdir();review.mkdir()
   k,p=case();compiled=compile_article(k,p)
   text='# 产品比较\n\n如何按照已知资料选择。\n\n## 比较标准\n\n植萃组合和乳液质地说明清洁效果好。\n\n只按可用资料选择。\n'
   for path in (writer,review):
    atomic_json(path/'knowledge.json',k);atomic_json(path/'product.json',p);atomic_json(path/'writer_done.json',{'compilation':compiled});(path/'draft.md').write_text(text,encoding='utf8')
   atomic_json(writer/'claim_map.json',{'claims':[]});atomic_json(writer/'knowledge_to_sections.json',{'sections':[{'section_id':'S1','knowledge_ids':['KU3']}]})
   consumer_prompts.build('review',review)
   class Client:
    logic_calls=0
    def review_logic(self,location,directory,meta):
     self.logic_calls+=1;data=logic.build_input(location);result=LogicTests().passing(data)
     if '说明清洁效果好' in (location/'draft.md').read_text('utf8'):
      result.update(verdict='revise',issues=[{'kind':'unsupported_inference','paragraph_ids':['P004'],'reason':'组成与外观不能支持清洁表现','repair':'去掉成分推功效'}]);result['checks']['no_causal_leap']=False
     return logic.certificate(result,data)
    def complete(self,prompt,directory,**kwargs):
     data=json.loads(prompt.split('资料：')[-1]);return {'decisions':[{'issue_id':v['id'],'classification':'confirmed_error','paragraph_ids':['P004'],'article_quote':'植萃组合和乳液质地说明清洁效果好。','source_ids':[],'source_quote':'','reason':'成分与质地不能证明成品清洁表现','repair':'删除未经支持的功效推断'} for v in data['proposals']]}
   client=Client();fact={'checks':{key:True for key in __import__('geo_source_cards.review_quality',fromlist=['FACT_CHECKS']).FACT_CHECKS},'claims':[],'failures':['C4：成分外观不能证明清洁效果'],'suggestions':[],'explanation':'独立审稿'}
   result=review_quality.process(client,review,fact,{})
   self.assertEqual(client.logic_calls,1);self.assertEqual(result['quality_status'],'needs_revision');atomic_json(review/'result.json',result)
   paragraph_repair.prepare(writer,'Semantic review requests revision')
   spec=json.loads((writer/'paragraph_repair.json').read_text('utf8'));old=next(p for p in spec['paragraphs'] if p['id']=='P004')
   answer={'base_sha256':spec['base_sha256'],'edits':[{'paragraph_id':'P004','old_sha256':old['sha256'],'text':'可以按已记录的组成与规格比较，成分与质地不能证明成品清洁表现。','evidence_ids':[]}]}
   fixed=paragraph_repair.apply(writer,answer)['draft_markdown'];self.assertNotEqual(text_hash(fixed),text_hash(text));self.assertIn('如何按照已知资料选择。',fixed)
   (review/'draft.md').write_text(fixed,encoding='utf8')
   with self.assertRaisesRegex(ValueError,'Stale'):review_quality.process(client,review,result,{})
   fresh=base/'fresh';fresh.mkdir()
   for name in ('knowledge.json','product.json','writer_done.json'):atomic_json(fresh/name,json.loads((writer/name).read_text('utf8')))
   (fresh/'draft.md').write_text(fixed,encoding='utf8');consumer_prompts.build('review',fresh)
   fact.update(failures=[]);out=review_quality.process(client,fresh,fact,{})
   self.assertEqual(client.logic_calls,2);self.assertEqual(out['logic_review']['status'],'passed');self.assertEqual(out['quality_status'],'reviewed')
   self.assertEqual(out['quality_pipeline']['draft_sha256'],text_hash(fixed))
 def test_three_roles_materialize_structure_kb_word_and_current_review(self):
  import zipfile
  from geo_source_cards.article_compiler import prepare
  from geo_source_cards import api_worker,consumer_prompts,review_quality,article_logic as logic
  from geo_source_cards.staged_editorial import sha
  from tests.test_article_logic import LogicTests
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
   root=Path(tmp);writer=root/'writer';review=root/'review';writer.mkdir();review.mkdir();k,p=case();k['reference_design']['primary_url']='https://example.test/original'
   original={'observations':[{'sources':[{'url':k['reference_design']['primary_url'],'article':{'status':'fetched','title':'如何比较资料','text':'先说明比较的问题。\n\n再按照不同对象逐项展开。','paragraphs':[{'kind':'paragraph','text':'先说明比较的问题。'},{'kind':'paragraph','text':'再按照不同对象逐项展开。'}]}}]}]}
   atomic_json(root/'research/research_input.json',original);atomic_json(root/'research/research_result.json',{'knowledge_units':k['knowledge_units']})
   atomic_json(writer/'knowledge.json',k);atomic_json(writer/'product.json',p)
   class Client:
    def __init__(self):self.roles=[];self.structure_tasks=[]
    def complete(self,prompt,directory,**kwargs):
     data=json.loads(next(line for line in prompt.splitlines() if line.startswith('{'))) if prompt.startswith('你是Structure Analyzer') else json.loads(prompt.split('资料：')[-1])
     if 'blocks' in data:
      self.roles.append('Structure Analyzer');return a.fallback(data,[])
     if kwargs.get('stage')=='review':
      self.roles.append('Article Reviewer');return {'checks':{key:True for key in review_quality.FACT_CHECKS},'claims':[],'failures':[],'suggestions':[],'explanation':'Mock逐项检查'}
     self.roles.append('Article Writer');task=data['task'];self.structure_tasks.append(task.get('structure_task'))
     claims=data['claims'];ids=task['claim_ids'][:1];claim=next((c for c in claims if c['id'] in ids),None)
     fact=(task.get('subject','') or '')+(claim['text'] if claim else '围绕当前比较问题展开。')
     text=fact+task['id']+'可以从已知规格开始考虑自己的选择需要，保留不同产品有依据的信息。缺少的项目先不作比较，再回到开头的问题，按相同的条件整理各项选择。读者可以把关注的问题放回自己的购买条件中，再比较实际记录过的规格和组成，这样每个部分都能共同回答同一个选择问题。'
     return {'id':task['id'],'title':'产品资料比较','heading':task['topic'],'paragraphs':[{'text':text,'statement_type':'product_fact' if claim else 'general_advice','claim_ids':ids}]}
    def review_logic(self,location,directory,meta):
     self.roles.append('Article Reviewer');data=logic.build_input(location);return logic.certificate(LogicTests().passing(data),data)
   client=Client();structure=a.analyze(client,writer,writer,k,{})
   atomic_json(writer/'writing_job.json',{'job_id':sha(json.dumps(original,ensure_ascii=False,sort_keys=True))[:24],'prompt_sha256':'mock'})
   compiled=prepare(writer,writer);self.assertEqual(compiled['article_structure']['sha256'],structure['sha256'])
   answer=w.generate(client,writer,{});api_worker.materialize({'stage':'writer','meta':{}},writer,answer)
   draft=(writer/'draft.md').read_text('utf8');self.assertIn(p['name'],draft);self.assertIn('200ml',draft);self.assertTrue(any(client.structure_tasks))
   with zipfile.ZipFile(writer/'article.docx') as word:self.assertIn('word/document.xml',word.namelist())
   for name in ('knowledge.json','product.json','writer_done.json'):atomic_json(review/name,json.loads((writer/name).read_text('utf8')))
   (review/'draft.md').write_text(draft,encoding='utf8');message=consumer_prompts.build('review',review);fact=client.complete(message,review/'call',stage='review')
   result=review_quality.process(client,review,fact,{});review_quality.verify_final(result,draft,k,p)
   self.assertEqual(result['logic_review']['status'],'passed');self.assertEqual(result['quality_status'],'reviewed');self.assertEqual(client.roles[0],'Structure Analyzer');self.assertEqual(client.roles.count('Article Writer'),len(compiled['sections'])+2);self.assertEqual(client.roles.count('Article Reviewer'),2)

 def test_reviewer_unavailable_never_creates_pass_marker(self):
  from geo_source_cards.review_quality import process
  from geo_source_cards.consumer_prompts import build
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.consumer_prompts.evidence_units',return_value=[]):
   root=Path(tmp);k,p=case();atomic_json(root/'knowledge.json',k);atomic_json(root/'product.json',p);(root/'draft.md').write_text('# 主题\n\n完整正文。',encoding='utf8');build('review',root)
   with self.assertRaisesRegex(ValueError,'reviewer required'):process(object(),root,{'checks':{key:True for key in __import__('geo_source_cards.review_quality',fromlist=['FACT_CHECKS']).FACT_CHECKS},'claims':[],'failures':[]},{})
   self.assertFalse((root/'quality_pipeline.json').exists())
 def test_limits_continue_with_single_usable_unit_and_other_missing_products(self):
  from geo_source_cards.consumer_prompts import require_writer_material
  k,p=case();k['knowledge_units']=k['knowledge_units'][-1:]
  units,_,projection=require_writer_material(k,p,[])
  self.assertEqual(len(units),1);self.assertTrue(projection['products_without_neutral_details'])
  self.assertEqual(compile_article(k,p)['feasibility']['status'],'READY_WITH_LIMITS')
 def test_replan_is_persisted_and_two_round_cap_stops_third_repair(self):
  from geo_source_cards.repair_router import prepare,RepairBlocked
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.consumer_prompts.evidence_units',return_value=[]):
   root=Path(tmp);k,p=case();atomic_json(root/'knowledge.json',k);atomic_json(root/'product.json',p);(root/'draft.md').write_text('# 主题\n\n先说明问题。\n\n## 比较\n\n需要重新比较。',encoding='utf8')
   out=prepare(root,'排名依据不存在',attempts=0);self.assertEqual(out['action'],'REPLAN');self.assertTrue((root/'replan.json').exists());self.assertTrue(out['replan']['fresh_review_required'])
   with self.assertRaisesRegex(RepairBlocked,'REPAIR_EXHAUSTED'):prepare(root,'排名依据不存在',attempts=2)

if __name__=='__main__':unittest.main()

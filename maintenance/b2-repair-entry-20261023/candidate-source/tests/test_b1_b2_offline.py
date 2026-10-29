import copy,json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards import structure_analyzer as a,review_quality as q,review_arbitration as r,article_logic as logic
from geo_source_cards.article_compiler import compile_article
from geo_source_cards.runtime import atomic_json
from tests.test_article_compiler import case
from tests import test_article_logic as logic_helpers

FIX=Path(os.environ['GEO_OFFLINE_FIXTURES'])
def read(p):return json.loads(Path(p).read_text('utf8'))
def seal(s):s.pop('sha256',None);s['sha256']=a.digest(s);return s
def saved(label):return [read(FIX/(label+'-'+n+'.json')) for n in ('article_structure','knowledge','product')]

class SourceRoleTests(unittest.TestCase):
 def test_saved_review_product_descriptions_bind_to_actual_first_product(self):
  s,k,p=saved('review02');roles=a.normalize_roles(s);subjects=[v for v in roles if v['role']=='subject']
  self.assertEqual(len(subjects),10)
  out=a.bind(compile_article(k,p),s);own=next(v for v in out['sections'] if v['subject']==p['name'])
  self.assertEqual(own['structure_id'],subjects[0]['id']);self.assertNotEqual(own['structure_id'],s['sections'][0]['id'])
 def test_saved_ranking_untyped_paragraph_headings_are_found_without_category_dictionary(self):
  s,k,p=saved('ranking01');out=a.bind(compile_article(k,p),s)
  role=next(v for v in out['structure_role_review']['roles'] if v['role']=='subject')
  own=next(v for v in out['sections'] if v['subject']==p['name'])
  self.assertEqual(own['structure_id'],role['id']);self.assertIn(role['subject_anchor'],own['structure_binding']['source_block_ids'])
 def test_equivalent_descriptions_do_not_change_roles_or_slot_binding(self):
  for label in ('review02','ranking01'):
   s,k,p=saved(label);base=a.bind(compile_article(k,p),s);ids={v['id'] for v in a.normalize_roles(s) if v['role']=='subject'}
   for part in s['sections']:
    if part['id'] in ids:part.update(purpose='说明这个对象的组成和规格，展示已有资质与使用描述',required_content=['组成、资质、规格和记录的体验'])
   changed=a.bind(compile_article(k,p),seal(s))
   self.assertEqual([(x['id'],x['structure_id']) for x in base['sections']],[(x['id'],x['structure_id']) for x in changed['sections']])
 def test_actual_role_change_changes_binding_instead_of_following_old_position(self):
  s,k,p=saved('review02');first=next(v for v in a.normalize_roles(s) if v['role']=='subject');part=next(v for v in s['sections'] if v['id']==first['id'])
  anchor=part['source_block_ids'][0];block=next(v for v in s['source']['blocks'] if v['id']==anchor);block['text']='比较标准与维度'
  part.update(purpose='说明比较标准和口径',required_content=['比较维度'],source_block_ids=[anchor],source_quote=block['text'])
  out=a.bind(compile_article(k,p),seal(s));own=next(v for v in out['sections'] if v['subject']==p['name'])
  self.assertNotEqual(own['structure_id'],first['id']);self.assertEqual(a.normalize_roles(s)[1]['role'],'criteria')
 def test_original_specific_facts_never_become_new_requirements_even_with_safe_label(self):
  s,k,p=saved('review02');s['sections'][1].update(purpose='逐项介绍对象',required_content=['原品牌专利92%功效，价格199元'])
  out=a.bind(compile_article(k,p),seal(s));view=json.dumps(a.writer_view(s),ensure_ascii=False)
  tasks=json.dumps([x['structure_task'] for x in out['sections']],ensure_ascii=False)
  for bad in ('92%','199元','原品牌专利'):self.assertNotIn(bad,view+tasks)
 def test_three_categories_and_limited_material_remain_writeable(self):
  s,_,_=saved('review02')
  for category in ('洗发水','咖啡','路由器'):
   k,p=case(category=category,title='功效排行');c=compile_article(k,p);out=a.bind(c,s)
   self.assertTrue(out['feasibility']['writeable']);self.assertEqual(out['feasibility']['status'],'READY_WITH_LIMITS')
   own=next(v for v in out['sections'] if v['subject']==p['name']);self.assertEqual(own['structure_task']['role'],'subject')
 def test_ambiguous_role_is_pending_not_a_product_binding(self):
  from tests.test_three_agent_quality import AnalyzerTests
  data=AnalyzerTests().data();s=a.fallback(data,[])
  for part in s['sections']:part.update(purpose='说明事项',required_content=['待核对内容'])
  s.update(version=a.VERSION,source=data,input_sha256='offline');seal(s);k,p=case();out=a.bind(compile_article(k,p),s)
  own=next(v for v in out['sections'] if v['subject']==p['name'])
  self.assertIsNone(own['structure_id']);self.assertEqual(own['structure_binding']['status'],'needs_check')
 def test_comparison_opening_criteria_and_closing_are_distinct(self):
  s,_,_=saved('review02');part=s['sections'][1];part['purpose']='横向比较多款的共同属性与差异';part['source_block_ids']+=s['sections'][2]['source_block_ids'];seal(s)
  roles=a.normalize_roles(s);self.assertEqual(roles[0]['role'],'opening');self.assertEqual(roles[1]['role'],'comparison');self.assertEqual(roles[-1]['role'],'summary')

class CacheTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
  self.writer=self.root/'writer';self.review=self.root/'review';self.writer.mkdir();self.review.mkdir()
  self.k,self.p=case();self.text='# 比较\n\n可以按需求选择。\n\n## 比较标准\n\n可以考虑自己的购买条件。\n\n仍需根据个人需求选择。\n'
  for folder in (self.writer,self.review):
   atomic_json(folder/'knowledge.json',self.k);atomic_json(folder/'product.json',self.p);atomic_json(folder/'writer_done.json',{'compilation':compile_article(self.k,self.p)});(folder/'draft.md').write_text(self.text,encoding='utf8')
  atomic_json(self.root/'research/research_result.json',{'knowledge_units':self.k['knowledge_units']})
  atomic_json(self.root/'research/research_input.json',{'observations':[]})
  outer=self
  class MockClient:
   def __init__(self):self.calls=0
   def review_logic(self,location,directory,meta):
    self.calls+=1;data=logic.build_input(location);return logic.certificate(logic_helpers.LogicTests().passing(data),data)
   def complete(self,message,folder,**kwargs):
    self.calls+=1;data=json.loads(message.split('资料：')[-1]);return {'decisions':[{'issue_id':v['id'],'classification':'needs_check','paragraph_ids':[],'article_quote':'','source_ids':[],'source_quote':'','reason':'离线占位，无语义验收结论','repair':''} for v in data['proposals']]}
  self.client=MockClient();self.fact={'checks':{v:True for v in q.FACT_CHECKS},'claims':[],'failures':[],'suggestions':[]}
 def process(self):return q.process(self.client,self.review,copy.deepcopy(self.fact),{})
 def change(self,path):
  value=read(path);value['offline_changed']=True;atomic_json(path,value)
 def test_identical_inputs_reuse_final_cache_with_no_extra_requests(self):
  result=self.process();count=self.client.calls;self.assertEqual(q.process(self.client,self.review,result,{}),result);self.assertEqual(self.client.calls,count)
  q.verify_final(result,self.text,self.k,self.p,location=self.writer)
 def test_original_source_only_change_invalidates_final_and_preserves_old_evidence(self):
  result=self.process();marker=(self.review/'quality_pipeline.json').read_bytes();count=self.client.calls;self.change(self.root/'research/research_result.json')
  with self.assertRaisesRegex(ValueError,'Stale'):q.process(self.client,self.review,result,{})
  with self.assertRaisesRegex(ValueError,'Stale'):q.verify_final(result,self.text,self.k,self.p,location=self.writer)
  self.assertEqual(self.client.calls,count);self.assertEqual((self.review/'quality_pipeline.json').read_bytes(),marker)
  self.assertEqual(read(self.review/'review_cache_status.json')['status'],'needs_reaudit')
 def test_body_only_change_invalidates(self):
  result=self.process();(self.review/'draft.md').write_text(self.text+'新增正文',encoding='utf8')
  with self.assertRaisesRegex(ValueError,'Stale'):q.process(self.client,self.review,result,{})
 def test_product_only_change_invalidates(self):
  result=self.process();self.change(self.review/'product.json')
  with self.assertRaisesRegex(ValueError,'Stale'):q.process(self.client,self.review,result,{})
 def test_knowledge_only_change_invalidates(self):
  result=self.process();self.change(self.review/'knowledge.json')
  with self.assertRaisesRegex(ValueError,'Stale'):q.process(self.client,self.review,result,{})
 def test_each_mapping_contract_and_research_input_change_invalidates(self):
  result=self.process()
  for folder,name in [(self.writer,'claim_map.json'),(self.writer,'knowledge_to_sections.json'),(self.review,'writer_done.json'),(self.writer,'writer_done.json'),(self.root/'research','research_input.json')]:
   with self.subTest(name=name):
    path=folder/name;old=path.read_bytes() if path.exists() else None
    atomic_json(path,{'changed':name})
    with self.assertRaisesRegex(ValueError,'Stale'):q.process(self.client,self.review,result,{})
    if old is None:path.unlink()
    else:path.write_bytes(old)
 def test_span_mapping_change_invalidates(self):
  from geo_source_cards.consumer_prompts import build
  build('review',self.review);result=self.process();self.change(self.review/'claim_spans.json')
  with self.assertRaisesRegex(ValueError,'Stale'):q.process(self.client,self.review,result,{})
 def test_arbitration_batches_and_final_certificate_cannot_ignore_changed_sources(self):
  self.fact['failures']=['需核对普通建议']*4;result=self.process();count=self.client.calls
  data=r.context(self.review,result['arbitration']['source_review']);r.enforce(result,self.text,self.k,self.p,location=self.writer)
  r.batched(self.client,self.review/'arbitration-call',data,{})
  self.assertEqual(count,self.client.calls)
  self.change(self.root/'research/research_result.json')
  with self.assertRaisesRegex(ValueError,'Stale'):r.batched(self.client,self.review/'arbitration-call',data,{})
  with self.assertRaisesRegex(ValueError,'Stale'):r.enforce(result,self.text,self.k,self.p,location=self.writer)
  with self.assertRaisesRegex(ValueError,'Stale'):r.batched(self.client,self.review/'arbitration-call',r.context(self.review,result['arbitration']['source_review']),{})
  self.assertEqual(count,self.client.calls)
 def test_legacy_passed_without_source_binding_is_not_promoted(self):
  atomic_json(self.review/'quality_pipeline.json',{'answer_sha256':a.digest(self.fact)})
  with self.assertRaisesRegex(ValueError,'legacy'):self.process()
  legacy={'quality_pipeline':{'version':'review-quality-v1','draft_sha256':logic.text_hash(self.text),'evidence_sha256':a.digest({'knowledge':self.k,'product':self.p}),'independent_logic_executed':True}}
  with self.assertRaisesRegex(ValueError,'legacy'):q.verify_final(legacy,self.text,self.k,self.p)
  self.assertEqual(self.client.calls,0)
 def test_review_service_unavailable_is_not_a_pass(self):
  from geo_source_cards.deepseek_api import APIError
  with patch.object(self.client,'review_logic',side_effect=APIError('review_unavailable')):
   with self.assertRaises(APIError):self.process()
  self.assertFalse((self.review/'quality_pipeline.json').exists())
 def test_unknown_arbitration_request_is_preserved_without_call(self):
  from geo_source_cards.deepseek_api import APIError
  data=r.context(self.review,{'failures':['待核对']*4});folder=self.root/'unknown-arbitration'
  path=folder/'batch-000/api_state.json';atomic_json(path,{'state':'REQUEST_UNKNOWN'});old=path.read_bytes()
  for _ in range(2):
   with self.assertRaises(APIError):r.batched(self.client,folder,data,{})
  self.assertEqual(path.read_bytes(),old);self.assertEqual(self.client.calls,0)
 def test_delivery_checks_sources_even_without_optional_logic_policy(self):
  import hashlib
  from creation import runtime,article_export
  result=self.process();folder=self.root/'approved/2026-10-23/排行类/01';folder.mkdir(parents=True)
  (folder/'draft.md').write_text(self.text,encoding='utf8');(folder/'article.docx').write_bytes(b'offline-fixture')
  for name,data in [('semantic_review.json',result),('logic_product.json',self.p),('logic_review.json',result['logic_review'])]:atomic_json(folder/name,data)
  files={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}
  atomic_json(folder/'receipt.json',{'status':'accepted_for_user_review','files':files,'word_sha256':files['article.docx'],'review_source_location':str(self.writer.relative_to(self.root))})
  meta={'task_name':'离线样例','category':'排行类','primary_reference':{}}
  with patch.object(article_export,'info',return_value=meta):
   self.assertEqual(runtime.articles(self.root)[0]['quality_status'],'ready')
   self.change(self.root/'research/research_result.json')
   row=runtime.articles(self.root)[0];self.assertEqual(row['quality_status'],'needs_revision')
   self.assertTrue(any('sources' in s for s in row['quality_issues']))

if __name__=='__main__':unittest.main()

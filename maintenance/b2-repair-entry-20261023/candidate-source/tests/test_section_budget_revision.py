import json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards import section_writer as w
from geo_source_cards.runtime import atomic_json
from tests import test_three_agent_quality as helpers

class SectionBudgetRevisionTests(unittest.TestCase):
 def test_long_part_retries_only_that_part_and_revision_reaches_every_call(self):
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':1400,'min_lead_hanzi':180,'max_chars':4800}):
   root=Path(tmp);helper=helpers.SectionTests();helper.setup_root(root)
   (root/'revision_note.txt').write_text('删除内部原文表述并压缩重复说明。',encoding='utf8')
   calls=[]
   class Client:
    def complete(self,message,folder,**kwargs):
     data=json.loads(message.split('资料：')[-1]);task=data['task'];calls.append((task['id'],data['revision_requirements']))
     if task['id']=='S1' and folder.name=='attempt-1':
      self_test.assertIsNotNone(data['rejected_section_to_correct'])
      self_test.assertIn('最多'+str(task['max_chars'])+'字符',message)
     size=task['max_chars']+1 if task['id']=='S1' and folder.name=='attempt-0' else task['target_hanzi']
     return {'id':task['id'],'title':'可用信息比较','heading':task['topic'],'paragraphs':[{'text':task['id']+'内容'*((size+1)//2),'claim_ids':[],'statement_type':'general_advice'}]}
   self_test=self
   out=w.generate(Client(),root,{})
   self.assertEqual(sum(i=='S1' for i,_ in calls),2)
   self.assertEqual(sum(i=='INTRO' for i,_ in calls),1)
   self.assertTrue(all('压缩重复说明' in revision for _,revision in calls))
   self.assertTrue(out['document']['sections'])
   first=json.loads((root/'section_calls/S1/attempt-0/section_failure.json').read_text())
   self.assertIn('character budget',first['reason'])
   (root/'revision_note.txt').write_text('另一版本要求',encoding='utf8')
   before=len(calls)
   with self.assertRaisesRegex(ValueError,'input/version'):w.generate(Client(),root,{})
   self.assertEqual(len(calls),before)
 def test_allocation_keeps_global_limit_and_rejects_short_introduction(self):
  tasks=[{'id':'INTRO','target_hanzi':580},{'id':'S1','target_hanzi':600,'product_detail_contract':{'minimum_hanzi':480}},{'id':'END','target_hanzi':180}]
  w.bound_lengths(tasks,{'max_chars':2000,'min_lead_hanzi':500})
  self.assertLessEqual(sum(t['max_chars'] for t in tasks)+140+80+4*len(tasks),2000)
  self.assertEqual(tasks[0]['minimum_hanzi'],500)
  value={'id':'INTRO','title':'问题','paragraphs':[{'text':'中'*499,'statement_type':'general_advice','claim_ids':[]}]}
  with self.assertRaisesRegex(ValueError,'shorter'):w.validate_part(value,tasks[0],{'claims':[]})
  value['paragraphs'][0]['text']='中'*500
  w.validate_part(value,tasks[0],{'claims':[]})
 def test_original_brand_assertions_are_not_new_requirements_or_opening_tasks(self):
  from geo_source_cards import structure_analyzer as a
  from tests.test_article_compiler import case
  from geo_source_cards.article_compiler import compile_article
  data=helpers.AnalyzerTests().data();source=a.fallback(data,[])
  base=source['sections'][0]
  source['sections']=[
   {**base,'id':'AS001','order':1,'purpose':'用生活场景建立共鸣，预告十款清单','required_content':['掉发原因与十款预告']},
   {**base,'id':'AS002','order':2,'purpose':'推介首迷产品的资质与配方功效','required_content':['首迷独有专利与92%防脱率','pH5.8与质地']},
   {**base,'id':'AS003','order':3,'purpose':'回扣问题并作综合结论','required_content':['首迷第一名']}]
  source.update(version=a.VERSION,source=data,input_sha256='input');source['sha256']=a.digest(source)
  k,p=case();c=a.bind(compile_article(k,p),source)
  view=json.dumps(a.writer_view(source),ensure_ascii=False)
  self.assertNotIn('首迷',view);self.assertNotIn('92%',view);self.assertNotIn('十款',view)
  self.assertEqual(c['article_structure']['sections'][1]['required_content'],source['sections'][1]['required_content'])
  own=next(s for s in c['sections'] if s['subject']==p['name'])
  self.assertEqual(own['structure_id'],'AS002')
  self.assertNotIn('生活场景',json.dumps(c['sections'][0]['structure_task'],ensure_ascii=False))
  self.assertNotIn('首迷',json.dumps(own['structure_task'],ensure_ascii=False))
 def test_retry_feedback_distinguishes_short_body_from_missing_fact_links(self):
  from tests.test_article_compiler import case
  from geo_source_cards.article_compiler import compile_article
  k,p=case();c=compile_article(k,p);task=w.plan(c,{'min_body_hanzi':100,'min_lead_hanzi':20})[1]
  value={'id':task['id'],'heading':'依据','paragraphs':[{'text':'组成直接证明效果。','statement_type':'inference','claim_ids':[]}]}
  with self.assertRaisesRegex(ValueError,'Fact without claim at paragraph 1'):w.validate_part(value,task,c)
  task.update(max_chars=300,minimum_hanzi=100)
  value['paragraphs'][0].update(statement_type='general_advice')
  with self.assertRaisesRegex(ValueError,'received 8 Hanzi, minimum 100'):w.validate_part(value,task,c)
  message=w.prompt(c,[task],task,[],'Section body substantially shorter than its task',rejected=value)
  self.assertIn('补充已有事实',message)
  self.assertNotIn('正文超限，压缩重复解释',message)
 def test_heading_alias_or_planned_heading_preserves_prose_but_never_fills_body(self):
  task={'id':'S1','topic':'固定比较依据','target_hanzi':1,'claim_ids':[]}
  for extra,expected in (({'title':'模型小标题'},'模型小标题'),({},'固定比较依据')):
   value={'id':'S1','paragraphs':[{'text':'可以按需求比较。','statement_type':'general_advice','claim_ids':[]}],**extra}
   self.assertEqual(w.validate_part(value,task,{'claims':[]})['heading'],expected)
   self.assertEqual(value['paragraphs'][0]['text'],'可以按需求比较。')
  for value in ({'id':'S1','paragraphs':[]},{'id':'OTHER','paragraphs':[{'text':'内容'}]}):
   with self.assertRaises(ValueError):w.validate_part(value,task,{'claims':[]})
 def test_saved_heading_failure_recovers_without_another_request(self):
  with tempfile.TemporaryDirectory() as tmp,patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':100,'min_lead_hanzi':20}):
   root=Path(tmp);helper=helpers.SectionTests();helper.setup_root(root);client=helper.client()
   out=w.generate(client,root,{})
   accepted=root/'section_calls/S1/accepted.json';value=json.loads(accepted.read_text('utf8'));value['title']=value.pop('heading');accepted.unlink()
   atomic_json(root/'section_calls/S1/attempt-0/response.json',value)
   atomic_json(root/'section_calls/S1/attempt-0/section_failure.json',{'reason':'Missing section heading','known_failure':True})
   before=len(client.calls);out=w.generate(client,root,{})
   self.assertEqual(len(client.calls),before)
   manifest=json.loads((root/'section_calls/manifest.json').read_text())
   self.assertTrue(manifest['components']['S1']['local_heading_recovery'])
 def test_pruned_ku_never_replaces_own_or_competitor_slot_with_foreign_facts(self):
  from tests.test_article_compiler import case
  from geo_source_cards.article_compiler import compile_article
  for category in ('洗发水','咖啡','路由器'):
   k,p=case(category=category)
   k['knowledge_units'].append({'id':'KU_bad','type':'risk','content':'没有依据的功效','verification':'not_independently_verified'})
   k['outline']['sections'][1]['knowledge_ids']=['KU_bad']
   k['outline']['sections'][2]['knowledge_ids']=['KU_bad']
   c=compile_article(k,p);own=next(s for s in c['sections'] if s['id']=='S2')
   self.assertEqual(own['subject'],p['name']);self.assertEqual(own['knowledge_ids'],[])
   claims={v['id']:v for v in c['claims']}
   self.assertTrue(own['claim_ids']);self.assertTrue(all(claims[i]['source_ids'][0].startswith('PF') for i in own['claim_ids']))
   other=next(s for s in c['sections'] if s['id']=='S3')
   self.assertEqual(other['subject'],k['reference_design']['products'][0]['name'])
   self.assertNotIn('KU2',other['knowledge_ids'])
   self.assertTrue(all(other['subject'] in claims[i]['subjects'] for i in other['claim_ids']))
   k['product_gate']['decision']='NO_INSERT';c=compile_article(k,p)
   self.assertFalse(any(s['subject']==p['name'] for s in c['sections']))
   self.assertFalse(any(v['source_ids'][0].startswith('PF') for v in c['claims']))

if __name__=='__main__':unittest.main()

"""Extra acceptance requirements; generated prose below is synthetic routing data."""
import copy,json,math,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards import structure_analyzer as a,section_writer as w,review_quality as q,repair_router as router
from geo_source_cards.article_compiler import compile_article,validate_document
from geo_source_cards.runtime import atomic_json
from geo_source_cards.article_logic import text_hash
from tests import test_b1_b2_offline as fixtures
saved,seal=fixtures.saved,fixtures.seal

def ambiguous(label):
 s,k,p=saved(label)
 # Keep the saved original and exact anchors. Simulate an analyzer that groups
 # all products into one broad comparison, with no individual product position.
 s['sections']=[{**s['sections'][0],'id':'AS001','order':1,'purpose':'横向比较多款的共同属性与差异',
  'required_content':['比较可支持的共同维度'],'source_block_ids':[b['id'] for b in s['source']['blocks']],
  'source_quote':s['source']['blocks'][0]['text'][:40]}]
 return seal(s),k,p

class NeedsCheckTests(unittest.TestCase):
 def compile(self,label='ranking01'):
  s,k,p=ambiguous(label);original=compile_article(k,p);return original,a.bind(original,s),k,p
 def test_saved_materials_pending_preserves_every_required_product_slot_and_identity(self):
  for label in ('ranking01','review02'):
   original,bound,k,p=self.compile(label)
   self.assertEqual([(s['id'],s.get('subject'),s['claim_ids']) for s in bound['sections']],[(s['id'],s.get('subject'),s['claim_ids']) for s in original['sections']])
   for section in bound['sections']:
    if section.get('subject'):
     self.assertIsNone(section['structure_id']);self.assertEqual(section['structure_binding']['status'],'needs_check')
     self.assertIn(section['id'],bound['structure_role_review']['pending_slots'])
   self.assertEqual(bound['feasibility'],original['feasibility'])
 def test_pending_writer_tasks_and_prompts_keep_the_complete_roster_without_importing_original_facts(self):
  original,bound,k,p=self.compile();tasks=w.plan(bound,{'min_body_hanzi':300,'min_lead_hanzi':20})
  self.assertEqual([t['id'] for t in tasks[1:-1]],[s['id'] for s in original['sections']])
  own=next(t for t in tasks if t.get('subject')==p['name']);data=json.loads(w.prompt(bound,tasks,own,[]).split('资料：')[-1])
  self.assertEqual(data['task']['structure_binding']['status'],'needs_check')
  self.assertEqual(data['task']['subject'],p['name']);self.assertEqual(data['task']['claim_ids'],own['claim_ids'])
  claims={c['id']:c for c in bound['claims']}
  self.assertTrue(all(p['name'] in claims[i]['subjects'] for i in own['claim_ids']))
  self.assertEqual(data['product_roster'],list(dict.fromkeys(s['subject'] for s in original['sections'] if s.get('subject'))))
 def generate(self):
  original,bound,k,p=self.compile();tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup);root=Path(tmp.name)
  for name,value in [('compilation.json',bound),('knowledge.json',k),('product.json',p)]:atomic_json(root/name,value)
  calls=[]
  class MockOnly:
   def complete(self,message,folder,**kw):
    task=json.loads(message.split('资料：')[-1])['task'];calls.append(task['id'])
    text=task['id']+'依据当前已知材料解释选择条件。'*math.ceil((task.get('minimum_hanzi',task['target_hanzi'])+20)/14)
    return {'id':task['id'],'title':'产品信息比较','heading':task['topic'],
     'paragraphs':[{'text':text,'statement_type':'general_advice','claim_ids':[]}]}
  with patch('geo_source_cards.genre_length.policy',return_value={'min_body_hanzi':300,'min_lead_hanzi':20}):out=w.generate(MockOnly(),root,{})
  return bound,out,calls
 def test_pending_mock_generation_does_not_skip_products_or_rebind_to_intro(self):
  contract,out,calls=self.generate();validate_document(out,contract,complete=True)
  self.assertEqual(calls,['INTRO',*[s['id'] for s in contract['sections']],'END'])
  self.assertEqual([s['id'] for s in out['document']['sections']],[s['id'] for s in contract['sections']])
 def test_pending_missing_or_empty_own_product_is_rejected_at_assembly(self):
  contract,out,_=self.generate();own=next(s['id'] for s in contract['sections'] if s.get('subject'))
  for mode in ('missing','empty'):
   bad=copy.deepcopy(out)
   if mode=='missing':bad['document']['sections']=[s for s in bad['document']['sections'] if s['id']!=own]
   else:next(s for s in bad['document']['sections'] if s['id']==own)['paragraphs']=[]
   with self.assertRaises(ValueError):validate_document(bad,contract,complete=True)

class SourcePathTests(unittest.TestCase):
 def setUp(self):
  self.h=fixtures.CacheTests();self.h.setUp();self.addCleanup(self.h.doCleanups)
  for folder in (self.h.writer,self.h.review):(folder/'draft.md').write_bytes(self.h.text.encode('utf8'))
  self.h.fact.update(draft_sha256=text_hash(self.h.text),
    claims=[{'text':'可以按需求选择。','supported':True,'evidence_ids':['KU3']}],explanation='仅为离线流程夹具')
 def test_finalizer_rejects_changed_sources_before_delivery(self):
  from geo_source_cards import daily_editorial as d
  h=self.h;result=h.process();atomic_json(h.review/'result.json',result);atomic_json(h.writer/'category.json',{})
  h.change(h.root/'research/research_result.json')
  with patch.object(d,'check',return_value={'failures':[]}),patch.object(d,'verify_delivery') as delivery:
   with self.assertRaisesRegex(ValueError,'Stale'):d.finalize(h.root,h.review)
   delivery.assert_not_called()
 def test_cache_rechecks_current_sources_before_returning_and_preserves_old_marker(self):
  h=self.h;result=h.process();old=(h.review/'quality_pipeline.json').read_bytes();count=h.client.calls
  h.change(h.root/'research/research_result.json')
  with self.assertRaisesRegex(ValueError,'Stale'):q.process(h.client,h.review,result,{})
  self.assertEqual(h.client.calls,count);self.assertEqual((h.review/'quality_pipeline.json').read_bytes(),old)
 def test_arbitrated_repair_rejects_changed_source(self):
  h=self.h;h.fact['failures']=['需要核对的建议']*4;result=h.process();self.assertIn('arbitration',result)
  h.change(h.root/'research/research_result.json')
  with self.assertRaisesRegex(ValueError,'Stale'):router.route(h.text,h.k,h.p,result,location=h.writer)
 def test_non_arbitrated_repair_must_reject_stale_source_before_routing(self):
  h=self.h;result=h.process();self.assertNotIn('arbitration',result)
  h.change(h.root/'research/research_result.json')
  with self.assertRaisesRegex(ValueError,'Stale'):router.route(h.text,h.k,h.p,result,reason='可以按需求选择。需检查这一段',location=h.writer)
 def test_non_arbitrated_repair_must_reject_stale_contract_before_routing(self):
  h=self.h;result=h.process();atomic_json(h.writer/'claim_map.json',{'changed':True})
  with self.assertRaisesRegex(ValueError,'Stale'):router.route(h.text,h.k,h.p,result,reason='可以按需求选择。需检查这一段',location=h.writer)
 def test_mid_review_source_change_cannot_issue_final_pass(self):
  h=self.h;original=h.client.review_logic
  def changed(*args,**kwargs):
   result=original(*args,**kwargs);h.change(h.root/'research/research_result.json');return result
  with patch.object(h.client,'review_logic',side_effect=changed):
   with self.assertRaisesRegex(ValueError,'Stale'):h.process()
  self.assertFalse((h.review/'quality_pipeline.json').exists())

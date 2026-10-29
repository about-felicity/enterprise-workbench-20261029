"""Source/version routing tests, not real model quality judgments."""
import copy,json,unittest
from unittest.mock import patch
from geo_source_cards import repair_router as r,review_quality as q,review_arbitration as arb,article_logic as logic
from geo_source_cards.runtime import atomic_json
from tests import test_b1_b2_offline as fixtures

REASON='可以考虑自己的购买条件。需核对这个段落。'

class EntryTests(unittest.TestCase):
 def setUp(self):
  self.h=fixtures.CacheTests();self.h.setUp();self.addCleanup(self.h.doCleanups);h=self.h
  for folder in (h.writer,h.review):(folder/'draft.md').write_bytes(h.text.encode('utf8'))
  h.fact['draft_sha256']=logic.text_hash(h.text);self.result=h.process();atomic_json(h.review/'result.json',self.result)
  self.calls=h.client.calls
 def change(self,path):
  value=json.loads(path.read_text('utf8')) if path.exists() else {};value['changed_by_test']=True;atomic_json(path,value)
 def rejected(self,*,review=None,text=None,knowledge=None,product=None):
  h=self.h;review=self.result if review is None else review
  before={p:p.read_bytes() for p in (h.review/'result.json',h.review/'quality_pipeline.json',h.review/'logic-call/logic_certificate.json')}
  for entry in ('route','prepare'):
   with self.subTest(entry=entry):
    if entry=='prepare':atomic_json(h.review/'result.json',review)
    with self.assertRaises(r.StaleReviewSources) as caught:
     if entry=='route':r.route(h.text if text is None else text,h.k if knowledge is None else knowledge,h.p if product is None else product,review,REASON,location=h.writer)
     else:r.prepare(h.writer,REASON)
    self.assertEqual(caught.exception.status,'needs_reaudit')
    self.assertEqual(json.loads((h.writer/'repair_source_status.json').read_text())['status'],'needs_reaudit')
  # Calling prepare writes no replacement review/certificate or new PATCH.
  for path,data in before.items():
   if path.name!='result.json' or review is self.result:self.assertEqual(path.read_bytes(),data)
  self.assertEqual(h.client.calls,self.calls)
  self.assertFalse((h.writer/'repair_route.json').exists())
 def test_original_research_change_rejects_both_entries_without_arbitration(self):
  self.assertNotIn('arbitration',self.result);self.change(self.h.root/'research/research_result.json');self.rejected()
 def test_research_input_change_rejects_both_entries(self):
  self.change(self.h.root/'research/research_input.json');self.rejected()
 def test_original_source_map_change_rejects_both_entries(self):
  self.change(self.h.root/'research/evidence_spans.json');self.rejected()
 def test_writer_source_map_change_rejects_both_entries(self):
  self.change(self.h.writer/'knowledge_to_sections.json');self.rejected()
 def test_claim_map_change_rejects_both_entries(self):
  self.change(self.h.writer/'claim_map.json');self.rejected()
 def test_contract_change_rejects_both_entries(self):
  self.change(self.h.writer/'writer_done.json');self.rejected()
 def test_compilation_change_rejects_both_entries(self):
  self.change(self.h.writer/'compilation.json');self.rejected()
 def test_disk_body_change_rejects_old_arguments_and_bound_false_branch(self):
  h=self.h;(h.writer/'draft.md').write_bytes((h.text+'新增说明。').encode('utf8'));self.rejected()
  with self.assertRaises(r.StaleReviewSources):r.route(h.text+'新增说明。',h.k,h.p,self.result,REASON,location=h.writer)
 def test_disk_knowledge_change_rejects_stale_caller_arguments(self):
  self.change(self.h.writer/'knowledge.json');self.rejected()
 def test_disk_product_change_rejects_stale_caller_arguments(self):
  self.change(self.h.writer/'product.json');self.rejected()
 def test_current_unchanged_inputs_keep_route_and_prepare_patch(self):
  h=self.h
  self.assertEqual(r.route(h.text,h.k,h.p,self.result,REASON,location=h.writer)['action'],'PATCH')
  self.assertEqual(r.prepare(h.writer,REASON)['action'],'PATCH');self.assertEqual(h.client.calls,self.calls)
 def test_missing_location_cannot_fall_back_to_old_certificate_location(self):
  h=self.h;self.assertTrue(self.result['quality_pipeline']['source_location'])
  for location in (None,'',h.root/'absent'):
   with self.subTest(location=str(location)),self.assertRaises(r.StaleReviewSources) as caught:r.route(h.text,h.k,h.p,self.result,REASON,location=location)
   self.assertEqual(caught.exception.status,'needs_reaudit')
  self.assertEqual(h.client.calls,self.calls)
 def test_missing_fingerprint_rejects_both_entries(self):
  bad=copy.deepcopy(self.result);bad['quality_pipeline'].pop('review_inputs_sha256');self.rejected(review=bad)
 def test_removed_pipeline_cannot_downgrade_persisted_modern_review_to_legacy(self):
  bad=copy.deepcopy(self.result);bad.pop('quality_pipeline');self.rejected(review=bad)
 def test_invalid_pipeline_marker_rejects_both_entries(self):
  for value in ({},None):
   bad=copy.deepcopy(self.result);bad['quality_pipeline']=value;self.rejected(review=bad)
 def test_missing_independent_review_evidence_rejects_both_entries(self):
  bad=copy.deepcopy(self.result);bad.pop('logic_review');self.rejected(review=bad)
 def test_stale_independent_review_evidence_rejects_both_entries(self):
  bad=copy.deepcopy(self.result);bad['logic_review']['input_sha256']='old';self.rejected(review=bad)
 def test_valid_revise_verdict_is_eligible_for_patch_not_required_to_pass(self):
  h=self.h;bad=copy.deepcopy(self.result);cert=bad['logic_review'];data=logic.build_input(h.writer)
  cert['review'].update(verdict='revise',issues=[{'kind':'contradiction','paragraph_ids':['P004'],'reason':'该段与当前选择条件需统一','repair':'修改本段'}])
  cert['review']['checks']['no_internal_contradiction']=False;cert['status']='needs_revision';logic.validate_result(cert['review'],data)
  self.assertEqual(r.route(h.text,h.k,h.p,bad,REASON,location=h.writer)['action'],'PATCH')
 def test_arbitration_independent_guard_is_retained(self):
  h=self.h;h.fact['failures']=['有待核对的建议']*4
  # Separate fresh fixture, leaving this test's first review evidence intact.
  other=fixtures.CacheTests();other.setUp();self.addCleanup(other.doCleanups)
  for folder in (other.writer,other.review):(folder/'draft.md').write_bytes(other.text.encode('utf8'))
  other.fact.update(draft_sha256=logic.text_hash(other.text),failures=['有待核对的建议']*4)
  result=other.process();atomic_json(other.review/'result.json',result)
  with patch.object(arb,'enforce',wraps=arb.enforce) as enforce:
   r.route(other.text,other.k,other.p,result,REASON,location=other.writer);enforce.assert_called_once()
  self.change(other.root/'research/research_result.json')
  for fn in (lambda:r.route(other.text,other.k,other.p,result,REASON,location=other.writer),lambda:r.prepare(other.writer,REASON)):
   with self.assertRaises(r.StaleReviewSources):fn()
 def test_changed_sources_do_not_replace_previous_patch_or_review(self):
  h=self.h;r.prepare(h.writer,REASON);old=(h.writer/'repair_route.json').read_bytes();review=(h.review/'result.json').read_bytes()
  self.change(h.root/'research/research_result.json')
  with self.assertRaises(r.StaleReviewSources):r.prepare(h.writer,REASON)
  self.assertEqual((h.writer/'repair_route.json').read_bytes(),old);self.assertEqual((h.review/'result.json').read_bytes(),review)
 def test_two_content_repairs_remain_hard_limit(self):
  h=self.h;out=r.route(h.text,h.k,h.p,self.result,REASON,attempts=2,location=h.writer);self.assertEqual(out['action'],'REPAIR_EXHAUSTED')
  with self.assertRaisesRegex(r.RepairBlocked,'REPAIR_EXHAUSTED'):r.prepare(h.writer,REASON,attempts=2)
  self.assertEqual(h.client.calls,self.calls)
 def test_unknown_and_old_arbitration_cache_protection_unchanged(self):
  for method in ('test_unknown_arbitration_request_is_preserved_without_call','test_arbitration_batches_and_final_certificate_cannot_ignore_changed_sources'):
   helper=fixtures.CacheTests();helper.setUp();self.addCleanup(helper.doCleanups);getattr(helper,method)()
 def test_old_final_cache_cannot_restore_stale_sources(self):
  h=self.h;self.change(h.root/'research/research_result.json')
  with self.assertRaisesRegex(ValueError,'Stale'):q.process(h.client,h.review,self.result,{})
  with self.assertRaisesRegex(ValueError,'Stale'):q.verify_final(self.result,h.text,h.k,h.p,location=h.writer)
  self.assertEqual(h.client.calls,self.calls)
 def test_budget_and_execution_lock_protection_unchanged(self):
  from tests.test_three_agent_quality import ExecutionProtectionTests
  ExecutionProtectionTests().test_generation_lock_blocks_duplicate_task_and_budget_failure_is_terminal()

if __name__=='__main__':unittest.main()

import json,unittest
from geo_source_cards.runtime import atomic_json,atomic_write
from geo_source_cards.paragraph_repair import prepare,apply
from geo_source_cards.delta_review import CHECKS,eligible,prompt,merge
from . import test_paragraph_repair as fixtures

class DeltaReviewTests(unittest.TestCase):
 def setUp(self):
  fixture=fixtures.ParagraphRepairTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
  self.fixture=fixture;self.writer=fixture.writer
  review=json.loads((self.writer.parent/'review/result.json').read_text('utf8'))
  review.update(checks={k:True for k in CHECKS},failures=[],claims=json.loads((self.writer/'claim_map.json').read_text('utf8'))['claims'],explanation='事实审核通过，逻辑需修订')
  for c in review['claims']:c['supported']=True
  atomic_json(self.writer.parent/'review/result.json',review)
  prepare(self.writer,'Logical review requests revision')
  result=apply(self.writer,fixture.answer());atomic_write(self.writer/'draft.md',result['draft_markdown'])
  audit=json.loads((self.writer/'paragraph_repair_audit.json').read_text('utf8'))
  atomic_json(self.writer/'writer_done.json',{'paragraph_repair_audit':audit})
 def test_only_unchanged_claims_are_reused_and_new_sentence_coverage_is_required(self):
  context=eligible(self.writer);self.assertIsNotNone(context)
  self.assertEqual(len(context['retained_claims']),1)
  self.assertIn('statement_decisions',prompt(self.writer))
  spans=json.loads((self.writer/'claim_spans.json').read_text('utf8'))
  response={'claims':[],'statement_decisions':[{'span_id':i,'class':'opinion','reason':'未提供价格，说明无法比较'} for i in spans]}
  result=merge(self.writer,response)
  self.assertEqual(len(result['claims']),1)
  self.assertTrue(result['incremental_fact_review']['fresh_whole_article_logic_review_required'])
  with self.assertRaisesRegex(ValueError,'missed edited'):merge(self.writer,{'claims':[],'statement_decisions':[]})
  response['statement_decisions'][0]['class']='fact'
  with self.assertRaisesRegex(ValueError,'missed factual'):merge(self.writer,response)
 def test_changed_untouched_text_or_evidence_forces_a_full_review(self):
  text=(self.writer/'draft.md').read_text('utf8');atomic_write(self.writer/'draft.md',text.replace('保留正确内容','偷偷改变内容'))
  self.assertIsNone(eligible(self.writer))
 def test_next_repair_spec_cannot_replace_the_applied_patch_evidence(self):
  spec=json.loads((self.writer/'paragraph_repair.json').read_text('utf8'))
  done=json.loads((self.writer/'writer_done.json').read_text('utf8'))
  atomic_json(self.writer/'writer_done.json',{**done,'paragraph_repair_spec':spec})
  atomic_json(self.writer/'paragraph_repair.json',{'base_sha256':'next-unapplied-repair'})
  self.assertIsNotNone(eligible(self.writer))
  (self.writer/'paragraph_repair.json').unlink()
  self.assertIsNotNone(eligible(self.writer))
 def test_a_failed_or_stale_prior_fact_review_cannot_be_reused(self):
  path=self.writer/'paragraph_repair.json';spec=json.loads(path.read_text('utf8'))
  spec['prior_fact_review']['checks']['no_unsupported_claims']=False;atomic_json(path,spec)
  self.assertIsNone(eligible(self.writer));self.assertIsNone(prompt(self.writer))

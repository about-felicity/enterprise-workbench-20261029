import copy,json,tempfile,unittest
from pathlib import Path
from geo_source_cards.paragraph_repair import prepare,apply,prompt
from geo_source_cards.article_logic import text_hash
from geo_source_cards.runtime import atomic_json,atomic_write

class ParagraphRepairTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
  self.writer=Path(self.temp.name)/'writer';self.writer.mkdir()
  self.text='# 产品比较\n\n开头回答具体问题。\n\n## 比较条件\n\n售价没有提供，却可以折算单位价格。\n\n保留正确内容与原有表达。\n'
  atomic_write(self.writer/'draft.md',self.text)
  atomic_json(self.writer/'product.json',{'name':'甲产品','facts':[{'approved':True,'text':'规格200ml。'}]})
  atomic_json(self.writer/'knowledge.json',{'knowledge_units':[{'id':'KU1','type':'opinion','content':'比较须有相同口径。','verification':'not_independently_verified'}],
    'outline':{'sections':[{'id':'S1','topic':'比较条件','knowledge_ids':['KU1']}]},'product_gate':{'decision':'LIGHT_MENTION'}})
  atomic_json(self.writer/'claim_map.json',{'claims':[{'text':'售价没有提供，却可以折算单位价格。','evidence_ids':['PF1']},{'text':'保留正确内容与原有表达。','evidence_ids':['KU1']}]})
  atomic_json(self.writer/'knowledge_to_sections.json',{'sections':[{'section_id':'S1','knowledge_ids':['KU1']}]})
  self.issues=[{'paragraph_ids':['P004'],'reason':'价格未知无法折算','repair':'保留未知'}]
  atomic_json(self.writer.parent/'review/result.json',{'draft_sha256':text_hash(self.text),'logic_review':{'review':{'issues':self.issues}}})
 def answer(self):
  spec=json.loads((self.writer/'paragraph_repair.json').read_text('utf8'))
  return {'base_sha256':spec['base_sha256'],'edits':[{'paragraph_id':'P004','old_sha256':spec['paragraphs'][3]['sha256'],
    'text':'售价没有提供，因此暂时无法折算单位价格。','evidence_ids':[]}]}
 def test_patch_preserves_untouched_prose_and_rebuilds_changed_claims(self):
  self.assertTrue(prepare(self.writer,'Logical review requests revision'))
  answer=self.answer();result=apply(self.writer,answer)
  self.assertEqual(result['draft_markdown'],self.text.replace('售价没有提供，却可以折算单位价格。','售价没有提供，因此暂时无法折算单位价格。'))
  self.assertEqual(result['claim_map']['claims'],[{'text':'保留正确内容与原有表达。','evidence_ids':['KU1']}])
  audit=json.loads((self.writer/'paragraph_repair_audit.json').read_text('utf8'))
  self.assertEqual(audit['edited_ids'],['P004']);self.assertTrue(audit['fresh_fact_and_logic_review_required'])
 def test_wrong_draft_hash_unknown_evidence_or_unapproved_paragraph_are_rejected(self):
  prepare(self.writer,'Logical review requests revision')
  for mutate in (lambda a:a.update(base_sha256='wrong'),lambda a:a['edits'][0].update(paragraph_id='P002'),
                 lambda a:a['edits'][0].update(evidence_ids=['PF999']),lambda a:a['edits'][0].update(text='新段\n\n另一段'),
                 lambda a:a['edits'].append(copy.deepcopy(a['edits'][0]))):
   answer=self.answer();mutate(answer)
   with self.assertRaises(ValueError):apply(self.writer,answer)
 def test_stale_review_cannot_authorize_current_paragraphs(self):
  atomic_json(self.writer.parent/'review/result.json',{'draft_sha256':'old','logic_review':{'review':{'issues':self.issues}}})
  from geo_source_cards.repair_router import RepairBlocked
  with self.assertRaisesRegex(RepairBlocked,'REVIEW_DISPUTED'):prepare(self.writer,'Old review rejected')
 def test_patch_prompt_replaces_the_full_writer_contract(self):
  prepare(self.writer,'Logical review requests revision')
  from geo_source_cards.api_prompts import build_prompt
  value=build_prompt({'stage':'writer','meta':{'paragraph_repair':True}},self.writer)
  self.assertIn('只修复指定段落',value);self.assertNotIn('"document":',value)
  data=json.loads(value.rsplit('\n资料：',1)[1]);self.assertEqual(data['repair']['editable_ids'],['P004'])
 def test_unchanged_context_edit_does_not_discard_a_valid_correction(self):
  prepare(self.writer,'Logical review requests revision',issues=[{'paragraph_ids':['P002','P004']}])
  spec=json.loads((self.writer/'paragraph_repair.json').read_text('utf8'));answer=self.answer()
  answer['edits'].append({'paragraph_id':'P002','old_sha256':spec['paragraphs'][1]['sha256'],'text':spec['paragraphs'][1]['text'],'evidence_ids':[]})
  result=apply(self.writer,answer)
  self.assertIn('因此暂时无法',result['draft_markdown'])
  self.assertEqual(json.loads((self.writer/'paragraph_repair_audit.json').read_text('utf8'))['ignored_byte_identical_edits'],['P002'])

import copy,json,tempfile,unittest
from pathlib import Path
from geo_source_cards import article_logic as l

class LogicTests(unittest.TestCase):
 def test_product_heading_cannot_be_repaired_over_unrelated_section_body(self):
  from geo_source_cards.consumer_prompts import document_answer
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);k={'reference_design':{'genre':'ranking','product_insertion':'FIRST_RECOMMENDATION','products':[{'name':'乙产品'}]},'product_gate':{'decision':'LIGHT_MENTION'},'outline':{'sections':[{'id':'S1','topic':'甲产品'},{'id':'S2','topic':'乙产品'}]},'knowledge_units':[{'id':'KU01','content':'乙产品规格10g'}]}
   (p/'knowledge.json').write_text(json.dumps(k));(p/'product.json').write_text(json.dumps({'name':'甲产品','facts':[{'text':'凝胶状','approved':True}]}))
   answer={'document':{'title':'2款产品','introduction':[],'sections':[{'id':'S1','heading':'选购思路','knowledge_ids':['KU01'],'paragraphs':[{'text':'只讨论通用方法，没有具体产品资料。','evidence_ids':['KU01']}]},{'id':'S2','heading':'甲产品','knowledge_ids':['KU01'],'paragraphs':[{'text':'甲产品为凝胶。','evidence_ids':['PF1']}]}]}}
   with self.assertRaisesRegex(ValueError,'不能靠改标题'):document_answer(answer,p)
 def product(self):return {'name':'甲品牌面膜','facts':[{'text':'凝胶状涂抹清洗型，清水洗净。','approved':True}]}
 def data(self,text):
  ps=l.segments(text);body=[p for p in ps if p['kind']=='body'];named=[p['id'] for p in body if '甲品牌面膜' in p['text']]
  return {'paragraphs':ps,'required_anchor_ids':list(dict.fromkeys([body[0]['id'],body[-1]['id']]+named[:1])),'draft_sha256':l.text_hash(text),'product_sha256':l.digest(self.product())}
 def passing(self,data):
  ids=data['required_anchor_ids'];p=ids[0];c=ids[-1]
  return {'verdict':'pass','main_question':'如何比较信息','answer':'按资料范围判断','checks':{k:True for k in l.CHECKS},'sequence':[{'id':h['id'],'role':'推进同一问题','needs':[],'coherent':True,'reason':'承接已有定义并继续比较'} for h in data['paragraphs'][1:] if h['kind']=='heading'],'links':[{'premise_ids':[p],'conclusion_ids':[ids[i%len(ids)]],'supported':True,'reason':str(i)+'对应已有说明'} for i in range(3)],'issues':[]}
 def test_pass_cannot_skip_reorder_or_use_future_section_as_prerequisite(self):
  d=self.data('# 标题\n\n背景。\n\n## 定义\n\n先说明概念。\n\n## 比较\n\n再按概念比较。\n\n## 收束\n\n结尾回答问题。')
  good=self.passing(d);l.validate_result(good,d)
  good['sequence'][0]['needs']=['P001','P002'];l.validate_result(good,d)
  good['sequence'][0]['needs']=['P004'];l.validate_result(good,d)
  for change in [lambda r:r['sequence'].pop(),lambda r:r['sequence'].reverse(),lambda r:r['sequence'][0].update(needs=[r['sequence'][1]['id']]),lambda r:r['sequence'][1].update(coherent=False)]:
   bad=copy.deepcopy(good);change(bad)
   with self.assertRaises(ValueError):l.validate_result(bad,d)
 def test_real_reported_failure_is_rejected_even_when_old_semantic_flags_pass(self):
  text='# 贴片面膜的配方表\n\n先看贴片面膜。\n\n甲品牌面膜是涂抹清洗型，用它解释上面的贴片配方。\n\n排序靠前更能说明配方用心程度。'
  data=self.data(text);result=self.passing(data);cert=l.certificate(result,data,l.deterministic_issues(text,self.product()))
  self.assertEqual(cert['status'],'needs_revision')
  with self.assertRaisesRegex(ValueError,'Logical review requests revision'):l.enforce(cert,text,self.product())
 def test_explicit_comparison_and_negative_inference_are_not_false_positive(self):
  text='# 贴片和涂抹面膜有什么区别\n\n先分清形态。\n\n甲品牌面膜是涂抹清洗型，不能证明贴片产品的表现。\n\n排序不能说明配方用心程度，也无法判断成本。'
  self.assertEqual(l.deterministic_issues(text,self.product()),[])
 def test_unmatched_form_rejected_before_writer_and_explicit_comparison_allowed(self):
  k={'reference_design':{'genre':'science','primary_title':'贴片面膜配方介绍'},'product_gate':{'decision':'LIGHT_MENTION'}}
  with self.assertRaisesRegex(ValueError,'未进行收费写作'):l.writer_preflight(k,self.product())
  k['reference_design']['primary_title']='贴片与涂抹面膜的区别';l.writer_preflight(k,self.product())
 def test_missing_checks_unknown_ids_and_uncovered_anchors_rejected(self):
  text='# 如何比较信息\n\n问题背景。\n\n甲品牌面膜列有用法。\n\n按同一对象比较。';data=self.data(text);good=self.passing(data)
  for mutate in [lambda r:r['checks'].pop('scope_consistent'),lambda r:r['links'][0].update(conclusion_ids=['P999']),lambda r:[v.update(conclusion_ids=['P002']) for v in r['links']]]:
   bad=copy.deepcopy(good);mutate(bad)
   with self.assertRaises(ValueError):l.validate_result(bad,data)
 def test_pass_with_false_link_or_rejection_without_evidence_rejected(self):
  d=self.data('# 标题\n\n前提。\n\n结论。');r=self.passing(d);r['links'][0]['supported']=False
  with self.assertRaises(ValueError):l.validate_result(r,d)
  r=self.passing(d);r['verdict']='revise'
  with self.assertRaises(ValueError):l.validate_result(r,d)
 def test_certificate_is_bound_to_draft_and_frozen_product(self):
  text='# 比较资料\n\n问题。\n\n甲品牌面膜的形态。\n\n结论。';d=self.data(text);c=l.certificate(self.passing(d),d)
  l.enforce(c,text,self.product())
  with self.assertRaises(ValueError):l.enforce(c,text+'改变正文',self.product())
  with self.assertRaises(ValueError):l.enforce(c,text,{'name':'后来换的产品','facts':[]})
 def test_specific_rejection_can_hold_article_without_claiming_full_coverage(self):
  text='# 标题\n\n前提。\n\n甲品牌面膜例子。\n\n结论。';d=self.data(text);r=self.passing(d)
  r['verdict']='revise';r['checks']['example_relevant']=False
  for link in r['links']:link['conclusion_ids']=['P002']
  r['issues']=[{'kind':'scope_shift','paragraph_ids':['P003'],'reason':'例子对象发生变化','repair':'保持同一对象'}]
  l.validate_result(r,d)
  c=l.certificate(r,d)
  with self.assertRaises(ValueError):l.enforce(c,text,self.product())

if __name__=='__main__':unittest.main()

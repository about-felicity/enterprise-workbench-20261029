import unittest
from geo_source_cards.product_richness import profile,contract,check
from geo_source_cards.consumer_prompts import reader_facts
from geo_source_cards.article_allocation import allocate,validate_quotas

class RichnessTests(unittest.TestCase):
 def test_structured_paragraph_accepts_level_three_headings_without_paid_rewrite(self):
  import tempfile,json
  from pathlib import Path
  from geo_source_cards.consumer_prompts import document_answer
  with tempfile.TemporaryDirectory() as tmp:
   loc=Path(tmp);(loc/'knowledge.json').write_text(json.dumps({'outline':{'sections':[{'id':'S1','topic':'配方'}]},'reference_design':{'genre':'science'}}));(loc/'product.json').write_text(json.dumps({'name':'示例'}))
   a={'document':{'title':'选择方法','introduction':[{'text':'读者的问题。','evidence_ids':[]}],'sections':[{'id':'S1','heading':'组成','knowledge_ids':['KU01'],'paragraphs':[{'text':'### 配方组成\n成分包括甘油与透明质酸钠。','evidence_ids':['PF1']},{'text':'### 标示用法','evidence_ids':[]},{'text':'依照包装步骤使用。','evidence_ids':['PF2']}]}],'conclusion':[]}}
   result=document_answer(a,loc)
   self.assertIn('### 配方组成\n\n成分包括甘油',result['draft_markdown'])
   self.assertEqual(result['claim_map']['claims'][0]['text'],'成分包括甘油与透明质酸钠。')
   self.assertTrue((loc/'document_projection.json').exists())
   a['document']['introduction'][0]['text']='## 未授权章节'
   with self.assertRaises(ValueError):document_answer(a,loc)

 def test_capture_projection_keeps_literal_neutral_product_evidence_only(self):
  from geo_source_cards.genre_outline import captured_neutral_details
  b={'genre':'ranking','products':[{'name':'甲面膜'},{'name':'乙面膜'}]}
  spans={'R1_1':{'quote':'甲面膜：质地为透明凝胶，28天皱纹改善90%，温和适用所有敏感肌。'},'R2_1':{'quote':'乙面膜：成分包括甘油和透明质酸钠，孕妇均可使用。'}}
  a=captured_neutral_details({'units':[]},b,spans)
  self.assertEqual([u['evidence'] for u in a['units']],[['R1_1'],['R2_1']])
  self.assertNotIn('90%',str(a));self.assertNotIn('孕妇',str(a));self.assertNotIn('敏感肌',str(a))
  self.assertIn('透明凝胶',str(a));self.assertIn('甘油',str(a))

 def test_report_summary_keeps_conditions_and_values_without_claiming_verification(self):
  r={'id':'R-2','method':'称重法','conditions':'20℃，45%RH','result':'相对保湿率143.77%','limitation':'不是人体含水量变化','source_quote':'真实来源中的检测摘要原句'}
  product={'facts':[{'text':'品牌提供的R-2摘要：20℃下称重法相对保湿率143.77%。','approved':True,'evidence_class':'supplier_report_summary','report':r}]}
  fact=reader_facts(product)[0];self.assertIn('143.77%',fact['text']);self.assertEqual(fact['report']['method'],'称重法')
  del r['conditions'];self.assertEqual(reader_facts(product),[])
 def test_detail_gate_requires_distinct_actual_product_facts_and_meaningful_length(self):
  product={'writing_profile':{'ranking_hanzi':200,'science_hanzi':200,'ranking_facts':2,'science_facts':2}}
  a='产品规格与包装组成的实际资料。'*8;b='品牌提供的检测摘要及试验条件。'*8
  facts=[{'id':'PF1'},{'id':'PF2','evidence_class':'supplier_report_summary'}]
  claims=[{'text':a,'evidence_ids':['PF1']},{'text':b,'evidence_ids':['PF2']}]
  errors,metrics=check(a+'\n\n'+b,product,True,claims,facts);self.assertEqual(errors,[]);self.assertEqual(len(metrics['used_fact_ids']),2)
  self.assertTrue(check(a,product,True,claims,facts)[0]);self.assertEqual(contract({},True),{})
  with self.assertRaises(ValueError):profile({'ranking_hanzi':1000})
 def test_explicit_genre_quotas_cannot_be_filled_with_the_other_genre(self):
  pools={'排行类':[(str(i),'r'+str(i)) for i in range(20)],'科普类':[('s','s')]}
  result=allocate(pools,14,['排行类','科普类'],{'排行类':7,'科普类':7})
  self.assertEqual(len(result['selected']['排行类']),7);self.assertEqual(result['planned'],8);self.assertEqual(result['genre_shortfalls']['科普类'],6)
  with self.assertRaises(ValueError):validate_quotas({'排行类':7,'科普类':8},14)

import json,tempfile,unittest
from pathlib import Path
from geo_source_cards.product_identity import bind,matches,for_validation
from geo_source_cards.reference_design import product_blocks,validate_structure
from geo_source_cards.genre_outline import bind as outline
from geo_source_cards.genre_prompts import build

class ProductIdentityTests(unittest.TestCase):
 def test_legacy_missing_identity_uses_frozen_product_without_mutating_knowledge(self):
  import copy
  b={'genre':'ranking','product_insertion':'FIRST_RECOMMENDATION','products':[{'name':'乙品牌面霜'}]}
  before=copy.deepcopy(b);p={'name':'甲品牌面霜','brand':'甲品牌'}
  draft='## 选购标准\n## 1. 甲品牌面霜\n## 2. 乙品牌面霜\n## 结尾总结'
  self.assertTrue(validate_structure(draft,b,include_length=False))
  self.assertEqual(validate_structure(draft,for_validation(b,p),include_length=False),[])
  self.assertEqual(b,before)
 def test_conflicting_explicit_product_cannot_be_silently_replaced(self):
  b={'owned_product':{'name':'原任务产品'},'products':[]}
  with self.assertRaisesRegex(ValueError,'identity conflict'):for_validation(b,{'name':'后来修改的产品'})
  self.assertIs(for_validation(b,{'name':'原任务产品'}),b)
 def test_cosmetic_roster_preserves_names_and_rejects_feature_prose(self):
  text='一、选购标准\n1.甲品牌美白精华霜\n成分列有甘油。\n2.乙品牌面霜（清爽款）\n配方资料。\n普通面霜\n选面霜要看标签。'
  self.assertEqual([p['name'] for p in product_blocks({'text':text})],['甲品牌美白精华霜','乙品牌面霜'])
 def test_owned_brand_and_competitor_order_are_task_specific(self):
  b=bind({'genre':'ranking','product_insertion':'FIRST_RECOMMENDATION','products':[{'name':'乙品牌面霜'}]}, {'name':'焕颜计小白罐美白精华霜','brand':'焕颜计'})
  good='## 标准\n## 1 焕颜计小白罐美白精华霜\n## 2 乙品牌面霜\n## 总结'
  self.assertEqual(validate_structure(good,b,include_length=False),[])
  self.assertTrue(validate_structure(good.replace('焕颜计小白罐美白精华霜','科熙本洗发水'),b,include_length=False))
  self.assertTrue(matches('焕颜计产品',b));self.assertFalse(matches('科熙本',b))
  a={'units':[{'id':'KU1','kind':'source_claim','text':'乙品牌面霜列有甘油','evidence':['R1_1']},{'id':'KU2','kind':'opinion','text':'按需求比较','evidence':['R0_1']}],'sections':[]}
  self.assertEqual(outline(a,b)['sections'][1]['topic'],'焕颜计小白罐美白精华霜')
 def test_prompt_does_not_insert_previous_brand(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'product.json').write_text(json.dumps({'name':'焕颜计小白罐美白精华霜','brand':'焕颜计','facts':[]}),encoding='utf8')
   b=bind({'version':'two-genre-v1','genre':'ranking','products':[]},{'name':'焕颜计小白罐美白精华霜','brand':'焕颜计'})
   value=build('writer',root,{'reference_design':b,'knowledge_units':[],'outline':{},'product_gate':{'decision':'LIGHT_MENTION'}})
   self.assertIn('焕颜计小白罐美白精华霜',value);self.assertNotIn('科熙本',value)

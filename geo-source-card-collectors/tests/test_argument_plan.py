import json,tempfile,unittest
from pathlib import Path
from geo_source_cards.argument_plan import build,canonical_title

class ArgumentPlanTests(unittest.TestCase):
 def fixture(self,kind='洗发水'):
  product={'name':'甲牌'+kind,'brand':'甲牌','facts':[{'approved':True,'text':'规格200ml。'},{'approved':True,'text':'组成包括甘油。'}]}
  knowledge={'reference_design':{'genre':'review','primary_title':'两款产品怎么比较','products':[{'name':'乙牌'+kind}]},
    'product_gate':{'decision':'LIGHT_MENTION'},'outline':{'sections':[{'id':'S1','topic':'比较维度','knowledge_ids':['KU2']},
    {'id':'S2','topic':product['name'],'knowledge_ids':['KU2']},{'id':'S3','topic':'乙牌'+kind,'knowledge_ids':['KU1']}]},
    'knowledge_units':[{'id':'KU1','type':'source_claim','content':'乙牌'+kind+'规格100ml，参考价格90元。','verification':'not_independently_verified'},
                       {'id':'KU2','type':'opinion','content':'可以按实际规格和购买条件作比较。','verification':'not_independently_verified'}]}
  return knowledge,product
 def test_unknown_price_and_packaging_remain_unknown_across_product_categories(self):
  for kind in ('洗发水','精华液','咖啡'):
   k,p=self.fixture(kind);plan=build(k,p)
   self.assertEqual(plan['products'][0]['fields']['price']['state'],'unknown')
   self.assertEqual(plan['products'][0]['fields']['packaging']['state'],'unknown')
   self.assertEqual(plan['products'][1]['fields']['price']['state'],'recorded')
   self.assertEqual(plan['products'][0]['fields']['net_content']['evidence_ids'],['PF1'])
   self.assertEqual(plan['comparison_dimensions'],['net_content'])
   self.assertEqual(plan['sections'][2]['needs'],['S2'])
 def test_no_insert_excludes_owned_product_and_unapproved_facts(self):
  k,p=self.fixture();k['product_gate']['decision']='NO_INSERT';p['facts'].append({'approved':False,'text':'售价100元。'})
  plan=build(k,p);self.assertEqual(plan['product_count'],1)
  self.assertNotIn('PF3',plan['facts'])
 def test_title_counts_distinguish_total_from_additional_products(self):
  self.assertEqual(canonical_title('9款选购参考：甲产品及9款对照',9),'9款选购参考：甲产品及8款对照')
  self.assertEqual(canonical_title('甲产品与9款口碑产品比较',10),'甲产品与9款口碑产品比较')
 def test_unverified_identifiers_are_not_reintroduced_from_a_failed_draft(self):
  from geo_source_cards.argument_plan import issues,title_counts_match
  k,p=self.fixture();p['facts'].append({'approved':True,'text':'备案编号AB12345678，尚未独立核验。'})
  findings=issues('# 两款产品\n\n甲牌洗发水有AB12345678，所以已备案。',k,p)
  self.assertEqual(findings[0]['paragraph_ids'],['P002'])
  self.assertTrue(title_counts_match('十一款参考：本品与十款对照',11))
  self.assertFalse(title_counts_match('十一款参考：本品与十一款对照',11))

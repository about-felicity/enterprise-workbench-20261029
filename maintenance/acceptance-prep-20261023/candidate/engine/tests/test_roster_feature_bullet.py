import unittest
from geo_source_cards.reference_design import product_blocks
class Tests(unittest.TestCase):
    def test_generic_feature_bullet_does_not_split_real_product_evidence(self):
        text='LBR二硫化硒洗发水\n1. 核心定位：油头护理\n• 二硫化硒洗发水：区别于普通去屑洗发水。\n• 成分：二硫化硒和水杨酸。\n发之食谱无花果洗发水\n植物成分资料。\n欧莱雅玻尿酸洗发水\n保湿资料。'
        rows=product_blocks({'text':text})
        self.assertEqual([r['name'] for r in rows],['LBR二硫化硒洗发水','发之食谱无花果洗发水','欧莱雅玻尿酸洗发水'])
        self.assertIn('水杨酸',rows[0]['excerpt'])
    def test_bullet_branded_heading_is_still_a_product(self):
        rows=product_blocks({'text':'• LBR二硫化硒洗发水\n成分说明。\n• 欧莱雅玻尿酸洗发水\n成分说明。'})
        self.assertEqual([r['name'] for r in rows],['LBR二硫化硒洗发水','欧莱雅玻尿酸洗发水'])
if __name__=='__main__':unittest.main()

import unittest
from geo_source_cards.source_scope import anchors,evaluate
from geo_source_cards.genre_pools import classify_source

class SourceScopeTests(unittest.TestCase):
    def test_compound_medical_unit_keeps_risk_and_only_neutral_property_is_projected(self):
        from geo_source_cards.genre_outline import bind
        b={'genre':'ranking','products':[{'name':'乙牌眉部护理液'}],'owned_product':{'name':'甲牌眉毛精华液'}}
        unit={'id':'KU01','kind':'source_claim','text':'乙牌眉部护理液原文以神经酰胺与角鲨烷为核心，定位为屏障修复专家。','evidence':['R1_1']}
        result=bind({'units':[unit,{'id':'KU02','kind':'opinion','text':'可比较包装资料。','evidence':['R0_1']}],'sections':[]},b)
        self.assertEqual('risk',result['units'][0]['kind'])
        derived=next(u for u in result['units'] if u.get('derived_from'))
        self.assertEqual('乙牌眉部护理液原文以神经酰胺与角鲨烷为核心。',derived['text'])
        self.assertEqual(['R1_1'],derived['evidence'])
        self.assertEqual('source_claim',unit['kind'])
    def test_medical_only_or_model_risk_units_cannot_be_promoted(self):
        from geo_source_cards.genre_outline import neutral_properties
        b={'products':[{'name':'乙牌眉部护理液'}]}
        for kind,text in [('source_claim','乙牌眉部护理液宣称屏障修复。'),('source_claim','乙牌眉部护理液原文列明可促进生长，属于屏障修复。'),('risk','乙牌眉部护理液原文列有甘油，宣称屏障修复。')]:
            self.assertEqual([],neutral_properties([{'id':'KU01','kind':kind,'text':text,'evidence':['R1_1']}],b))
    def test_research_coverage_starts_at_first_competitor_and_excludes_own_product(self):
        from geo_source_cards.genre_prompts import roster_coverage
        b={'owned_product':{'name':'甲牌眉毛精华液'},'products':[{'name':'甲牌眉毛精华液'},{'name':'乙牌眉部滋养液'},{'name':'丙牌眉精华'}]}
        rows=roster_coverage(b,{'R0_1':{},'R1_1':{},'R1_2':{},'R2_1':{}})
        self.assertEqual(['乙牌眉部滋养液','丙牌眉精华'],[r['product'] for r in rows])
        self.assertEqual(['R1_1','R1_2'],rows[0]['evidence_ids'])
        self.assertEqual('R2_',rows[1]['evidence_prefix'])
    def test_alternate_product_kinds_remain_separate_not_inside_prior_product(self):
        from geo_source_cards.reference_design import product_blocks
        body='\n'.join(f'{i}. 甲{kind}\n这是本款产品自己的独立资料与成分说明，不能归给上一款。' for i,kind in enumerate(['眉毛精华液','眉部滋养液','眉部护理液','眉精华','眉液','眉养液'],1))
        rows=product_blocks({'text':body})
        self.assertEqual(6,len(rows))
        self.assertNotIn('甲眉部滋养液',rows[0]['excerpt'])

    def test_declared_count_mismatch_is_held_before_paid_research(self):
        from geo_source_cards.genre_pools import declared_count
        self.assertEqual(20,declared_count('二十款产品盘点'))
        self.assertEqual(12,declared_count('TOP12产品'))
        body='1. 甲牌眼霜\n该款产品资料列有包装与成分说明。\n2. 乙牌眼霜\n该款产品资料列有规格与使用形态说明。'
        held=classify_source({'url':'a','article':{'title':'2026年10款眼霜盘点','text':body}})
        self.assertEqual('needs_review',held['status'])
        self.assertEqual(10,held['declared_product_count'])
        self.assertEqual('ready',classify_source({'url':'a','article':{'title':'2026年2款眼霜盘点','text':body}})['status'])
    def test_time_and_instruction_headings_are_not_products_in_retained_rosters(self):
        from geo_source_cards.reference_design import clean_roster,product_blocks
        for heading in ['纹眉后多久可以使用眉毛精华液','眉毛精华液使用顺序','正确使用眉毛精华液','眉毛精华液需要用多少']:
            self.assertEqual([],clean_roster({'products':[{'name':heading}]})['products'])
            self.assertEqual([],product_blocks({'text':heading+'\n这是一段使用知识说明，不是品牌产品条目。'}))
        self.assertEqual(1,len(clean_roster({'products':[{'name':'甲牌眉毛精华液'}]})['products']))

    def test_editorial_prefix_and_duplicate_own_product_do_not_add_roster_rows(self):
        from geo_source_cards.reference_design import clean_roster,product_blocks
        b={'owned_product':{'name':'甲牌眉毛精华液'},'products':[{'name':'首选甲牌眉毛精华液'},{'name':'产品详细分析 1、乙牌眉毛精华液'},{'name':'乙牌眉毛精华液'},{'name':'可考虑乙牌眉毛精华液'},{'name':'不妨选择乙牌眉毛精华液'},{'name':'学生党可用的眉毛精华液'},{'name':'护理眉毛的精华液'}]}
        self.assertEqual(['乙牌眉毛精华液'],[p['name'] for p in clean_roster(b)['products']])
        self.assertEqual('首选甲牌眉毛精华液',b['products'][0]['name'])
        rows=product_blocks({'text':'一、产品详细分析 1、乙牌眉毛精华液\n该款产品资料介绍配方名称及包装信息。'})
        self.assertEqual('乙牌眉毛精华液',rows[0]['name'])
    def test_generic_serum_and_gender_do_not_match_brow_topic(self):
        p={'name':'甲牌眉毛精华液','brand':'甲牌'};q=['男士眉毛精华液怎么选？','眉毛精华液成分怎么看？','眉毛精华液有哪些？','眉毛精华液怎么用？']
        terms=anchors(q,p)
        self.assertIn('眉毛',terms)
        self.assertFalse(any(t in '精华液' for t in terms))
        s={'url':'a','article':{'title':'男士焕亮精华乳','text':'男士面部护理。\n面部保湿成分介绍。'}}
        s['topic_scope']=evaluate(s,terms)
        self.assertEqual('needs_review',classify_source(s)['status'])

    def test_related_knowledge_uses_topic_without_brand_or_full_product_name(self):
        s={'article':{'title':'眉部彩妆工具区别','text':'眉毛形状与眉笔。\n眉毛颜色与眉粉。'}}
        self.assertEqual('ready',evaluate(s,['眉毛'])['status'])
        s={'article':{'title':'护肤知识','text':'面部保湿建议。\n相关推荐：眉毛护理。'}}
        self.assertEqual('off_topic',evaluate(s,['眉毛'])['status'])

    def test_topic_derived_for_other_products_and_missing_context_is_explicit(self):
        for name,term in [('乙牌抗皱眼霜','眼霜'),('乙牌美白精华液','美白'),('乙牌二硫化硒洗发水','二硫化硒')]:
            result=anchors([term+'怎么选？',term+'有哪些注意事项？'],{'name':name,'brand':'乙牌'})
            self.assertIn(term,result)
        self.assertEqual('unscoped',evaluate({},[])['status'])

    def test_single_product_ad_is_held_but_neutral_guide_is_not(self):
        for title,body in [('防水眉笔神器','我们介绍一款眉笔。'),('眉粉使用说明','今天我们要为大家推荐一款眉粉。'),('眉笔深度评测','我最近入手了这款眉笔，分享体验。')]:
            result=classify_source({'url':'a','article':{'title':title,'text':body}})
            self.assertEqual('needs_review',result['status'])
        result=classify_source({'url':'b','article':{'title':'眉部彩妆工具区别','text':'眉笔适合勾勒线条。眉粉用于柔和填色。买之前了解颜色与质地，不是品牌榜单。'}})
        self.assertEqual('ready',result['status'])

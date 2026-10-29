import unittest
from geo_source_cards.consumer_voice import issues

class ConsumerVoiceTests(unittest.TestCase):
    def test_source_commentary_is_not_a_consumer_article(self):
        for text in ['原文对面霜的定位很明确：它面向面部皮肤。','参考文章建议关注成分。','主参考先讲配方。','产品知识库中提到多个成分。','这一位置是文章编排的选择。']:
            self.assertTrue(issues('# 标题\n\n'+text), text)
    def test_repeated_attribution_is_style_advice_and_does_not_block_article(self):
        text='\n\n'.join(['品牌资料列有某成分，资料未提供浓度，不构成功效保证。']*5)
        from geo_source_cards.consumer_voice import warnings
        self.assertFalse(issues(text));self.assertTrue(warnings(text))
    def test_direct_product_information_with_one_disclosure_is_allowed(self):
        text='# 眼部护理产品怎么比较\n\n先明确自己在意的包装形态，再比较产品信息。\n\n甲牌眼霜规格为15g。本文与甲牌存在商业关联。\n\n成分表列有甘油。成分名称不能代替实际使用体验。'
        self.assertEqual([],issues(text))
    def test_quoted_process_language_is_still_rejected(self):
        self.assertTrue(issues('这篇文章不写“原文建议”之类的表达。'))
    def test_product_label_text_is_not_article_production_commentary(self):
        self.assertEqual([],issues('购买前可以查看瓶身标签原文、成分表原文与说明书原文，也可以索取检测报告原文。'))
        self.assertTrue(issues('成分表原文另存附件，参考原文认为该产品最好。'))
    def test_named_citation_and_normal_qualifications_are_not_process(self):
        self.assertEqual([],issues('据某媒体报道，这款产品采用泵头包装。\n\n成分表没有提供浓度，选购时可以进一步了解。'))
    def test_product_projection_keeps_pf_ids_and_omits_internal_comments(self):
        import copy
        from geo_source_cards.consumer_prompts import reader_facts
        p={'facts':[{'text':'产品名称：甲牌眼霜；资料来源为用户上传知识库，未独立核验。','approved':True},{'text':'知识库列有规格15g/支；具体信息以标签为准。','approved':True},{'text':'文档列有备案编号，未独立核验。','approved':True},{'text':'资料描述配有按摩头，不能推出促进吸收。','approved':True},{'text':'不将见效时间当效果。','approved':True},{'text':'资料成分介绍提及甘油；完整INCI未提供可核验附件。','approved':True}]}
        before=copy.deepcopy(p);r=reader_facts(p)
        self.assertEqual(before,p);self.assertEqual(['PF1','PF2','PF4','PF6'],[x['id'] for x in r])
        self.assertEqual([],issues('\n\n'.join(x['text'] for x in r)))
        self.assertIn('配有按摩头',r[2]['text']);self.assertNotIn('促进吸收',str(r))
    def test_pending_identifiers_cannot_lose_their_qualification_in_projection(self):
        from geo_source_cards.consumer_prompts import reader_facts
        p={'facts':[{'text':'知识库列有国妆特字G00001、人体测试编号A123、报告编号B456；状态与原件未独立核验。','approved':True,'independently_verified':False},{'text':'国妆特字G00002。','approved':True,'independently_verified':True},{'text':'产品编号SKU123，规格200ml。','approved':True}]}
        r=reader_facts(p)
        self.assertEqual([x['id'] for x in r],['PF2','PF3'])
        self.assertNotIn('A123',str(r));self.assertIn('SKU123',str(r))
    def test_structured_document_uses_the_same_text_for_claim_mapping(self):
        import json,tempfile
        from pathlib import Path
        from geo_source_cards.consumer_prompts import document_answer
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'knowledge.json').write_text(json.dumps({'outline':{'sections':[{'id':'S1'}]}}))
            a={'document':{'title':'选购参考','introduction':[{'text':'先明确自己的需求。','evidence_ids':[]}],'sections':[{'id':'S1','heading':'甲牌眼霜','knowledge_ids':['KU01'],'paragraphs':[{'text':'甲牌眼霜规格为15g。','evidence_ids':['PF2']}]}],'conclusion':[]}}
            result=document_answer(a,root)
            self.assertIn(result['claim_map']['claims'][0]['text'],result['draft_markdown'])
            a['document']['sections'][0]['id']='invented'
            self.assertRaises(ValueError,document_answer,a,root)
    def test_complete_section_ids_in_the_wrong_order_are_rejected(self):
        import json,tempfile
        from pathlib import Path
        from geo_source_cards.consumer_prompts import document_answer
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'knowledge.json').write_text(json.dumps({'outline':{'sections':[{'id':'S1'},{'id':'S2'}]}}))
            section=lambda n:{'id':n,'heading':n,'knowledge_ids':[],'paragraphs':[{'text':'有完整正文但顺序仍须核对。','evidence_ids':[]}]}
            a={'document':{'title':'比较说明','introduction':[],'sections':[section('S1'),section('S2')],'conclusion':[]}}
            self.assertIn('S1',document_answer(a,root)['draft_markdown'])
            a['document']['sections'].reverse()
            with self.assertRaisesRegex(ValueError,'original order'):document_answer(a,root)
    def test_unverified_effects_are_excluded_not_just_stripped_of_attribution(self):
        from geo_source_cards.consumer_prompts import reader_knowledge
        k={'reference_design':{'products':[{'name':'乙牌抗皱眼霜'}]},'knowledge_units':[{'id':'KU1','type':'source_claim','content':'乙牌抗皱眼霜配方含甘油，促进胶原生成。'},{'id':'KU2','type':'source_claim','content':'眼周皮肤厚度约为面部的三分之一。'},{'id':'KU3','type':'opinion','content':'选购时可比较包装和价格。'}],'outline':{'sections':[{'id':'S1','topic':'皮肤厚度','knowledge_ids':['KU2']}]}}
        units,outline,projection=reader_knowledge(k,{'name':'甲牌眼霜','facts':[]})
        self.assertEqual(['KU1','KU3'],[u['id'] for u in units]);self.assertNotIn('促进',units[0]['content'])
        self.assertEqual('乙牌抗皱眼霜配方含甘油。',units[0]['content']);self.assertNotIn('KU2',outline['sections'][0]['knowledge_ids'])
    def test_ranking_identity_is_compiled_from_outline_not_abbreviated_model_heading(self):
        import json,tempfile
        from pathlib import Path
        from geo_source_cards.consumer_prompts import document_answer
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);k={'reference_design':{'genre':'ranking','product_insertion':'FIRST_RECOMMENDATION','products':[{'name':'乙牌（BRAND）修护眼霜'}]},'product_gate':{'decision':'LIGHT_MENTION'},'outline':{'sections':[{'id':'S1','topic':'选购依据'},{'id':'S2','topic':'甲牌眼霜'},{'id':'S3','topic':'乙牌（BRAND）修护眼霜'}]}}
            k['knowledge_units']=[{'id':'KU01','content':'乙牌（BRAND）修护眼霜成分表列有甘油。'}]
            (root/'knowledge.json').write_text(json.dumps(k));(root/'product.json').write_text(json.dumps({'name':'甲牌眼霜','facts':[{'text':'成分表列有甘油。','approved':True}]}))
            a={'document':{'title':'10款眼霜参考','introduction':[{'text':'具体问题。','evidence_ids':[]}],'sections':[{'id':s['id'],'heading':'模型缩写','knowledge_ids':['KU01'],'paragraphs':[{'text':'成分表列有甘油。','evidence_ids':['PF1'] if s['id']=='S2' else ['KU01']}]} for s in k['outline']['sections']]}}
            result=document_answer(a,root)
            self.assertIn('# 2款眼霜参考',result['draft_markdown']);self.assertIn('## 2. 乙牌（BRAND）修护眼霜',result['draft_markdown'])
            self.assertEqual('模型缩写',a['document']['sections'][2]['heading']);self.assertTrue((root/'document_projection.json').exists())
    def test_neutral_attributes_can_be_recovered_from_the_same_verified_quote(self):
        from geo_source_cards.consumer_prompts import reader_knowledge
        k={'reference_design':{'genre':'ranking','products':[{'name':'乙牌抗皱眼霜'}]},'knowledge_units':[{'id':'KU1','type':'source_claim','content':'乙牌主打修护。'},{'id':'KU2','type':'opinion','content':'可以比较容量和包装。'}],'outline':{'sections':[{'id':'S1','topic':'乙牌抗皱眼霜','knowledge_ids':['KU1']}]}}
        evidence=[{'id':'KU1','evidence':[{'quote_id':'R1_2','url':'https://example.org','quote':'该产品配方列有甘油和丁二醇，宣称促进细胞吸收。'}]}]
        units,_,projection=reader_knowledge(k,{'name':'甲牌眼霜','facts':[]},evidence)
        self.assertIn('甘油和丁二醇',units[0]['content']);self.assertNotIn('吸收',units[0]['content'])
        self.assertEqual([],projection['products_without_neutral_details'])

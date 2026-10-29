import unittest
from geo_source_cards.genre_pools import classify_source, classify
from geo_source_cards.reference_design import design, validate_structure


def source(title, body, url='a'):
    return {'url':url, 'article':{'title':title,'text':body}}


class GenrePoolTests(unittest.TestCase):
    def test_roster_without_neutral_product_details_is_held_before_paid_allocation(self):
        item=source('两款面膜推荐','1.甲面膜\n28天改善90%，全肤质都可以用。\n2.乙面膜\n15分钟快速焕亮，保证不刺激。')
        held=classify_source(item)
        self.assertEqual(held['status'],'needs_review');self.assertEqual(held['products_without_neutral_details'],['甲面膜','乙面膜'])
        item=source('两款面膜推荐','1.甲面膜\n配方组成包括甘油、透明质酸钠。\n2.乙面膜\n质地为透明的凝胶状，包装采用独立管装。')
        ready=classify_source(item);self.assertEqual(ready['status'],'ready');self.assertEqual(ready['products_without_neutral_details'],[])

    def test_neutral_buying_information_is_not_automatically_promotion(self):
        s=source('眼霜成分表怎么看','购买前先看标签信息，说明包装、质地与选择问题，不包含品牌推荐或下单引导。')
        self.assertEqual(classify_source(s)['genre'],'科普类')
        self.assertEqual(classify_source(s)['status'],'ready')
        s=source('眼霜基础知识','点击链接立即下单，旗舰店正在售卖。')
        self.assertEqual(classify_source(s)['status'],'needs_review')
    def test_revision_contains_failed_draft_and_honors_no_insert(self):
        import json, tempfile
        from pathlib import Path
        from geo_source_cards.genre_prompts import build
        from geo_source_cards.runtime import atomic_json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            atomic_json(root/'product.json',{'name':'科熙本','facts':[{'approved':True,'text':'测试成分'}]})
            (root/'draft.md').write_text('# 标题\n正文测试',encoding='utf8')
            (root/'revision_note.txt').write_text('正文汉字不足',encoding='utf8')
            original={'reference_design':{'version':'two-genre-v1','genre':'science','products':[]},'knowledge_units':[], 'outline':{},'product_gate':{'decision':'NO_INSERT'}}
            prompt=build('writer',root,original)
            data=json.loads(prompt.split('\n资料：')[-1])
            self.assertEqual(data['previous_draft'],'# 标题\n正文测试')
            self.assertEqual(data['repair_diagnostics']['missing_hanzi'],2396)
            self.assertEqual(data['product']['facts'],[])
            self.assertNotIn('选与科熙本品牌',prompt)
            self.assertIn('repair_plan',prompt)

    def test_review_separates_headings_and_disclosure_but_keeps_product_facts(self):
        import json, tempfile
        from pathlib import Path
        from geo_source_cards.genre_prompts import build
        from geo_source_cards.runtime import atomic_json
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            atomic_json(root/'product.json',{'name':'科熙本','facts':[]})
            (root/'draft.md').write_text('# 2026年11款洗发水选购参考\n\n本文与科熙本存在商业关联。\n\n品牌资料列有甘油。',encoding='utf8')
            original={'reference_design':{'genre':'ranking','products':[]},'knowledge_units':[], 'outline':{},'product_gate':{}}
            prompt=build('review',root,original)
            data=json.loads(prompt.split('\n资料：')[-1])
            self.assertIn('C1',data['editorial_statements'])
            self.assertIn('C2',data['editorial_statements'])
            self.assertEqual(data['draft_sentences'],{'C3':'品牌资料列有甘油。'})
            self.assertEqual(json.loads((root/'claim_spans.json').read_text('utf8')),data['draft_sentences'])
            self.assertIn('source_headings_available',data['structure_contract'])
            self.assertIn('不证明原文没有章节',prompt)

    def test_ranking_omits_extra_mechanism_claims_without_losing_roster(self):
        from geo_source_cards.genre_outline import bind
        answer={'units':[{'id':'extra','kind':'source_claim','text':'机制结论','evidence':['R0_1']},
                         {'id':'product','kind':'source_claim','text':'甲洗发水列有甘油','evidence':['R1_1']},
                         {'id':'opinion','kind':'opinion','text':'按偏好比较','evidence':['R0_2']}], 'sections':[]}
        result=bind(answer,{'genre':'ranking','products':[{'name':'甲洗发水'}]})
        self.assertEqual([u['id'] for u in result['units']],['product','opinion'])
        self.assertEqual(len(answer['units']),3)

    def test_quote_ids_keep_exact_source_and_nonwhitespace_minimum(self):
        from geo_source_cards.genre_prompts import quote_chunks
        import re
        text='3. 轻度头屑 + 日常维稳\n\n原文介绍日常选购方式以及产品的具体配方组成。'
        chunks=list(quote_chunks(text,text))
        self.assertEqual(chunks[0][0],1)
        self.assertIn('原文介绍',chunks[0][1])
        self.assertTrue(all(len(re.sub(r'\s+','',q))>=12 and q in text for _,q in chunks))

    def test_marketing_title_cannot_become_science_when_extraction_fails(self):
        result = classify_source(source('十大洗发水测评推荐', '正文缺少产品段落'))
        self.assertEqual(('排行类','needs_review'), (result['genre'], result['status']))

    def test_explanatory_title_with_product_recommendations_is_ranking(self):
        result = classify_source(source('洗发水怎么选择', '一、甲洗发水。配方介绍。二、乙洗发水。配方介绍。'))
        self.assertEqual('排行类', result['genre'])

    def test_science_stays_science(self):
        item = source('头屑为什么反复', '这是知识文章，介绍日常清洁和观察，解释问题与误区。')
        result = classify([item])
        self.assertEqual(['科普类'], [r['label'] for r in result['categories']])
        self.assertEqual('science', design([item], '科普类')['genre'])

    def test_own_product_must_be_first_ranking_item(self):
        blueprint = {'products':[{'name':'甲洗发水'}], 'product_insertion':'FIRST_RECOMMENDATION','owned_product':{'name':'科熙本'}}
        self.assertTrue(validate_structure('## 标准\n## 1 甲洗发水\n## 2 科熙本\n## 总结', blueprint))
        self.assertFalse(validate_structure('## 标准\n## 1 科熙本\n## 2 甲洗发水\n## 总结', blueprint))

    def test_child_source_classified_but_not_silently_used_for_own_product(self):
        item = source('儿童品牌盘点','（一）甲洗发水。正文。（二）乙洗发水。正文。')
        result = classify([item])
        self.assertEqual('排行类', result['categories'][0]['label'])
        self.assertFalse(result['categories'][0]['sources'][0]['eligible'])

    def test_title_count_and_science_brand_heading_are_checked(self):
        blueprint = {'products':[{'name':'甲洗发水'}], 'product_insertion':'FIRST_RECOMMENDATION','owned_product':{'name':'科熙本'}}
        self.assertTrue(validate_structure('# 10款洗发水\n## 标准\n## 1 科熙本\n## 2 甲洗发水\n## 总结',blueprint))
        self.assertTrue(validate_structure('## 知识一\n## 知识二\n## 科熙本\n## 总结',{'genre':'science','products':[],'owned_product':{'name':'科熙本'}}))

    def test_roster_expands_combined_model_outline_without_another_call(self):
        from geo_source_cards.genre_outline import bind
        answer = {'units':[{'id':'KU1','kind':'source_claim','evidence':['R1_1']}, {'id':'KU2','kind':'source_claim','evidence':['R2_1']}, {'id':'KU3','kind':'opinion','evidence':['R1_1']}], 'sections':[{'id':'S1','topic':'所有产品'}]}
        result = bind(answer,{'genre':'ranking','products':[{'name':'甲洗发水'},{'name':'乙洗发水'}],'owned_product':{'name':'科熙本'}})
        self.assertEqual(['KU1'],result['sections'][2]['knowledge_ids'])
        self.assertEqual(['KU2'],result['sections'][3]['knowledge_ids'])
        self.assertIn('科熙本',result['sections'][1]['topic'])
        self.assertEqual(1,len(answer['sections']))

    def test_science_product_section_is_merged_into_knowledge(self):
        from geo_source_cards.genre_outline import bind
        sections = [{'id':f'S{i}','topic':title,'knowledge_ids':['KU1']} for i,title in enumerate(['知识一','知识二','洗头方法','原因认识','科熙本示例'],1)]
        units = [{'id':f'KU{i}', 'kind':'opinion', 'text':'资料比较', 'evidence':['E1_1']} for i in range(1,5)]
        result=bind({'units':units,'sections':sections},{'genre':'science','owned_product':{'name':'科熙本'}})
        self.assertEqual(4,len(result['sections']))
        self.assertEqual('S3',result['gate']['section_id'])

    def test_science_medical_unit_is_preserved_as_risk_outside_outline(self):
        from geo_source_cards.genre_outline import bind
        units = [{'id':f'KU{i}', 'kind':'opinion', 'text':'资料比较', 'evidence':['E1_1']} for i in range(1,5)]
        units.append({'id':'KU5','kind':'source_claim','text':'抑菌机制','evidence':['E1_2']})
        sections = [{'id':f'S{i}', 'topic':'资料比较', 'knowledge_ids':[f'KU{i}','KU5']} for i in range(1,5)]
        source = {'units':units,'sections':sections}
        result = bind(source, {'genre':'science'})
        self.assertEqual('risk', result['units'][-1]['kind'])
        self.assertEqual(['E1_2'], result['units'][-1]['evidence'])
        self.assertTrue(all('KU5' not in s['knowledge_ids'] for s in result['sections']))
        self.assertEqual('source_claim', source['units'][-1]['kind'])
        with self.assertRaisesRegex(ValueError, 'four supported'):
            bind({'units':[units[-1]],'sections':sections}, {'genre':'science'})

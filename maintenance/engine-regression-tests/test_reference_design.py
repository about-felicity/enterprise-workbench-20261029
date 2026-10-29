import unittest
from geo_source_cards.reference_design import compatible, product_blocks, design, validate_structure


class ReferenceDesignTests(unittest.TestCase):
    def test_action_advice_is_never_a_product_even_if_it_contains_a_category_name(self):
        from geo_source_cards.reference_design import clean_roster
        actions=['频繁更换洗发水','不要频繁更换防脱洗发水','正确涂抹面膜','反复使用眼霜']
        text='\n'.join(str(i)+'.'+name+'\n这是一条日常使用建议，不能当作一个产品来计算。' for i,name in enumerate(actions,1))
        self.assertEqual(product_blocks({'text':text}),[])
        self.assertEqual(clean_roster({'products':[{'name':n} for n in actions]})['products'],[])
        kept=clean_roster({'products':[{'name':'甲牌防脱洗发水'},{'name':'乙牌滋润眼霜'}]})
        self.assertEqual(len(kept['products']),2)
    def test_form_categories_are_not_independent_products_even_in_retained_rosters(self):
        from geo_source_cards.reference_design import clean_roster
        names=['清洁型涂抹面膜','滋养型涂抹面膜','修护型涂抹面膜','免洗涂抹睡眠面膜']
        body='\n'.join(str(i+1)+'. '+n+'\n质地和用法有详细介绍。' for i,n in enumerate(names))
        self.assertEqual(product_blocks({'text':body}),[])
        self.assertEqual(clean_roster({'products':[{'name':n} for n in names]})['products'],[])
        kept=clean_roster({'products':[{'name':'示例品牌保湿涂抹面膜'}]})['products']
        self.assertEqual(len(kept),1)
        self.assertTrue(any('独立产品' in x for x in validate_structure('## 类型',{'genre':'ranking','products':[{'name':n} for n in names]},include_length=False)))

    def test_longform_outline_is_checked_for_structure_without_body_length(self):
        blueprint = {'version':'two-genre-v1', 'genre':'ranking',
                     'product_insertion':'FIRST_RECOMMENDATION', 'products':[{'name':'甲洗发水'}],'owned_product':{'name':'科熙本'}}
        outline = '## 选购维度\n## 1 科熙本\n## 2 甲洗发水\n## 总结'
        self.assertFalse(validate_structure(outline, blueprint, include_length=False))
        self.assertTrue(any('正文汉字不足' in e for e in validate_structure(outline, blueprint)))
        self.assertTrue(validate_structure(outline.replace('甲洗发水','乙洗发水'), blueprint, include_length=False))

    def test_roster_uses_heading_not_marketing_description_or_body_prose(self):
        text = ('一、2026 去屑洗发水选购标准\n三、分层推荐（按配方）1.御草朵草本洗发水\n'
                '1. 成分列表：侧柏叶、当归\n2. 配方特点：植物组合\n'
                '2.首迷洗发水\n核心定位：头皮微生态调理型去屑洗发水。\n'
                '3.吕（Ryo）紫吕去屑洗发水\n列有水杨酸和人参。\n'
                '四、使用贴士\n取适量洗发水于掌心。\n选洗发水要看需求。')
        products = product_blocks({'text': text})
        self.assertEqual([p['name'] for p in products], ['御草朵草本洗发水', '首迷洗发水', '吕（Ryo）紫吕去屑洗发水'])
        self.assertIn('侧柏叶、当归', products[0]['excerpt'])
        self.assertIn('植物组合', products[0]['excerpt'])
        self.assertNotIn('使用贴士', products[-1]['excerpt'])

    def test_standalone_headings_and_summary_detail_deduplicate(self):
        text = ('甲洗发水综合评分：9分\n乙洗发水综合评分：8分\n'
                '甲洗发水——配方介绍\n配方列有泛醇、甘油和侧柏叶提取物，规格为300ml。\n'
                '乙洗发水\n配方列有氨基酸和保湿成分。\n'
                '丙洗发水（清爽款）\n列有薄荷提取物和甘油。')
        # Numbered summaries followed by unnumbered detailed headings are one list.
        text = '1.' + text.replace('\n乙洗发水综合', '\n2.乙洗发水综合', 1)
        products = product_blocks({'text': text})
        self.assertEqual([p['name'] for p in products], ['甲洗发水', '乙洗发水', '丙洗发水'])
        self.assertIn('侧柏叶', products[0]['excerpt'])
        self.assertNotIn('综合评分', products[0]['excerpt'])

    def test_child_mention_does_not_override_adult_title(self):
        self.assertFalse(compatible("儿童洗发水温和选购", "敏感掉发洗发水品牌盘点"))
        self.assertTrue(compatible("儿童洗发水温和选购", "宝宝洗发水怎么选"))

    def test_flattened_product_headings_and_country_suffix(self):
        article = {"text": "导语（一）甲草本洗发液——介绍。正文。（二）Vichy Dercos 敏感头皮版（法国）描述。（三）乙温和洗发水（美国）描述。（四）如果你用清凉洗发水。"}
        names = [p["name"] for p in product_blocks(article)]
        self.assertEqual(names, ["甲草本洗发液", "Vichy Dercos 敏感头皮版", "乙温和洗发水"])

    def test_no_generic_four_sections_can_pass_product_roundup(self):
        blueprint = {"products": [{"name": "甲洗发水"}, {"name": "乙洗发水"}, {"name": "丙洗发水"}]}
        self.assertTrue(validate_structure("## 容量\n## 价格\n## 香气\n## 结尾", blueprint))
        good = "## 选购标准\n## 一、甲洗发水\n描述\n## 二、乙洗发水\n描述\n## 三、丙洗发水\n描述\n## 总结"
        self.assertFalse(validate_structure(good, blueprint))

    def test_incompatible_primary_is_excluded_before_writing(self):
        body = "（一）甲洗发水。介绍。（二）乙洗发水。介绍。（三）丙洗发水。介绍。"
        sources = [{"url": "adult", "article": {"title": "成人敏感头皮盘点", "text": body}}, {"url": "child", "article": {"title": "儿童洗发水盘点", "text": body}}]
        result = design(sources, "儿童洗发水温和选购")
        self.assertEqual("child", result["primary_url"])
        self.assertEqual("NO_INSERT", result["product_insertion"])

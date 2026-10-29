import unittest
from geo_source_cards.article_quality import normalize
from geo_source_cards.genre_pools import classify_source

class ArticleQualityTests(unittest.TestCase):
 def test_comment_and_trending_shell_is_not_full_text(self):
  raw='某作者\n\n评论 84\n\n'+''.join('今日热门新闻条目\n' for _ in range(80))
  result=normalize({'status':'fetched','text':raw,'title':'面霜能当眼霜吗icon_voice_onicon_voice'})
  self.assertEqual(result['status'],'failed');self.assertEqual(result['rejected_text'],raw)
 def test_genuine_body_survives_and_ui_tail_removed(self):
  body='选购时查看产品标签与包装信息，区分原料名称与成品资料。'*15
  result=normalize({'status':'fetched','text':body+'\n\n评论\n热榜','title':'知识讲解icon_voice_onicon_voice'})
  self.assertEqual(result['status'],'fetched');self.assertEqual(result['text'],body);self.assertEqual(result['title'],'知识讲解')
 def test_comparison_markers_never_fall_back_to_science(self):
  for title,body in [('10大眼霜怎么选','没有识别到产品条目'),('热门眼霜深度横评','正文'),('眼霜选购攻略','接下来把7款眼霜的特点说清楚。')]:
   result=classify_source({'url':'https://example.org/a','article':{'title':title,'text':body}})
   self.assertEqual((result['genre'],result['status']),('排行类','needs_review'))
 def test_question_heading_is_not_an_extra_product_or_title_count(self):
  from geo_source_cards.reference_design import product_blocks,validate_structure
  text='1、甲品牌眼霜\n资料组成。\n2、乙品牌眼霜\n资料组成。\n眼周敏感肌怎么挑选眼霜\n查看标签。'
  self.assertEqual([p['name'] for p in product_blocks({'text':text})],['甲品牌眼霜','乙品牌眼霜'])
  bp={'products':[{'name':'甲品牌眼霜'},{'name':'眼周敏感肌怎么挑选眼霜'}],'owned_product':{'name':'自有眼霜'},'product_insertion':'FIRST_RECOMMENDATION'}
  self.assertFalse(validate_structure('# 2款眼霜\n## 选购标准\n## 自有眼霜\n## 甲品牌眼霜\n## 总结',bp))
 def test_description_does_not_split_a_product_excerpt(self):
  from geo_source_cards.reference_design import product_blocks
  body='去眼袋第一名的眼霜！正文说明。\n\n1、甲品牌眼霜\n\n主要功效：是甲品牌旗下的一款眼霜。\n\n核心成分：资料列有甘油。\n\n使用感受：来源中的主观描述。\n\n2、乙品牌眼霜\n\n规格：15g。'
  rows=product_blocks({'text':body});self.assertEqual([r['name'] for r in rows],['甲品牌眼霜','乙品牌眼霜'])
  self.assertIn('核心成分',rows[0]['excerpt']);self.assertIn('使用感受',rows[0]['excerpt'])
 def test_name_only_list_is_held_before_paid_research(self):
  result=classify_source({'url':'https://example.org','article':{'title':'两款产品盘点','text':'1、甲品牌眼霜\n2、乙品牌眼霜'}})
  self.assertEqual(result['status'],'needs_review')
 def test_append_repair_only_handles_pure_length_failures(self):
  from geo_source_cards.append_repair import eligible_error
  self.assertTrue(eligible_error('Draft checks rejected: 正文汉字不足：2271，至少2400; 科普导语至少200汉字'))
  self.assertFalse(eligible_error('Draft checks rejected: 正文汉字不足：2271; 发现连续复制来源文本的片段'))
  self.assertFalse(eligible_error('Draft checks rejected: 正文超过最大长度'))

if __name__=='__main__':unittest.main()

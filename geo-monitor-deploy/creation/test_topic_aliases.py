import unittest
from geo_source_cards.source_scope import evaluate

class TopicAliasesTests(unittest.TestCase):
 def test_styling_synonyms_match(self):
  for word in ['定型喷雾','塑型喷雾','发型喷雾','蓬松喷雾']:
   value=evaluate({'article':{'title':'敏感头皮如何选择温和'+word,'text':''}},['造型喷雾'])
   self.assertEqual(value['status'],'ready')
   self.assertIn(word,value['matched_aliases']['造型喷雾'])
 def test_cosmetic_sprays_and_unrelated_topics_remain_excluded(self):
  for title in ['定妆喷雾购买指南','保湿喷雾推荐','香水喷雾测评','防晒喷雾哪个好']:
   self.assertEqual(evaluate({'article':{'title':title,'text':''}},['造型喷雾'])['status'],'off_topic')
 def test_footer_single_mention_not_enough(self):
  self.assertEqual(evaluate({'article':{'title':'护肤知识','text':'保湿方法。\n相关推荐：定型喷雾。'}},['造型喷雾'])['status'],'off_topic')

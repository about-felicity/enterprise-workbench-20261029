import unittest
from geo_source_cards.article_title import normalize,display_title

class ArticleTitleTests(unittest.TestCase):
 def test_preserve_existing_title_and_body(self):
  text='# 控油洗发水怎么选？\n\n导语。\n\n## 正文\n内容。\n'
  self.assertEqual(normalize(text),text)
 def test_intro_is_preserved_not_truncated(self):
  body='秋风一至，头皮就开启换季模式。'*15+'\n\n**特点**\n\n正文。'
  fixed=normalize(body,{'name':'科熙本防脱精华'},{'category':'排行类'})
  self.assertTrue(fixed.endswith(body+'\n'));self.assertLessEqual(len(fixed.splitlines()[0]),82)
  self.assertEqual(normalize(fixed),fixed)
 def test_plain_title_is_promoted(self):
  self.assertEqual(normalize('**洗发水选购指南**\n\n正文。'),'# 洗发水选购指南\n\n正文。\n')
 def test_bad_h1_remains_body(self):
  paragraph='发缝变宽，头发细软。'*20
  fixed=normalize('# '+paragraph+'\n\n正文。')
  self.assertIn('\n\n'+paragraph,fixed)
 def test_question_in_intro_becomes_short_title_without_losing_intro(self):
  text='用什么洗发水头发不油？这是很多人反复搜索的问题。\n\n后文。'
  self.assertEqual(display_title(text),'用什么洗发水头发不油？');self.assertIn(text,normalize(text))
 def test_short_sentence_is_not_title(self):
  self.assertIn('\n\n头皮开始出油。',normalize('头皮开始出油。\n\n正文。'))
 def test_blank_and_bom(self):
  self.assertEqual(display_title(''),'未命名文章')

if __name__=='__main__':unittest.main()

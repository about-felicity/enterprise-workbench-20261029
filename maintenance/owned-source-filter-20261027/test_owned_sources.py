import sys,unittest,tempfile,json,importlib.util
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
spec=importlib.util.spec_from_file_location('creation.owned_sources','/tmp/owned-source-filter/owned_sources.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class OwnedTests(unittest.TestCase):
 def source(self,text,title='眉毛精华测评'):
  return {'url':'https://example.com/article','title':title,'article':{'status':'fetched','text':text}}
 def test_body_mentions_are_excluded(self):
  self.assertTrue(mod.ownership(self.source('竞品很好，梵玢 FBCY 眉毛精华液也在榜单里。'))['owned'])
 def test_any_own_product_not_only_task_product(self):
  self.assertTrue(mod.ownership(self.source('推荐科熙本控油蓬松洗发水'))['owned'])
 def test_negative_mention_still_excluded(self):
  self.assertTrue(mod.ownership(self.source('不推荐梵玢眉毛增长液'))['owned'])
 def test_title_only(self):
  self.assertTrue(mod.ownership(self.source('正文不重复品牌','姿生怡眼霜评测'))['owned'])
 def test_category_is_not_ownership(self):
  self.assertFalse(mod.ownership(self.source('眉毛精华液的刷头与日常保养方法'))['owned'])
 def test_question_does_not_contaminate_source(self):
  rows=[{'question':'梵玢眉毛精华液','sources':[self.source('其他品牌眉毛精华液评测')]}]
  kept,excluded=mod.exclude_owned(rows);self.assertEqual(len(kept),1);self.assertEqual(excluded,[])
 def test_audit_and_prepared_guard(self):
  rows=[{'sources':[self.source('科熙本植物防脱赋活多效精华液'),self.source('普通眉毛养护知识')]}]
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);kept,excluded=mod.exclude_owned(rows,root)
   self.assertEqual(len(kept[0]['sources']),1);self.assertEqual(len(excluded),1)
   (root/'geo_articles.jsonl').write_text(json.dumps(rows[0]),encoding='utf8')
   with self.assertRaisesRegex(ValueError,'自有产品信源'):mod.guard_prepared(root)
 def test_confirmed_url(self):
  source=self.source('正文未出现产品');source['url']='https://www.redsh.com/pinpai/20260905/051530.shtml'
  self.assertTrue(mod.ownership(source)['owned'])
if __name__=='__main__':unittest.main()

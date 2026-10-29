import unittest,importlib.util
spec=importlib.util.spec_from_file_location('geo_source_cards.rewrite_v2.normalization_candidate','/tmp/recovery-structure-parser.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Tests(unittest.TestCase):
 def fixture(self):return {'type':'json_object','article_type':'ranking','tone':'客观','article_structure':['开头','写作节奏：先总后分','特殊风格元素：对比','禁用模式：不复制原文']}
 def test_exact_tail_is_lossless_and_does_not_mutate(self):
  x=self.fixture();y=m.validate(x);self.assertEqual(y['writing_rhythm'],'先总后分');self.assertEqual(y['article_structure'],['开头']);self.assertEqual(len(x['article_structure']),4)
 def test_missing_tail_is_rejected(self):
  x=self.fixture();x['article_structure'].pop()
  with self.assertRaises(ValueError):m.validate(x)
 def test_unknown_metadata_is_rejected(self):
  x=self.fixture();x['extra']='untrusted'
  with self.assertRaises(ValueError):m.validate(x)
 def test_normal_schema_remains_valid(self):
  x=m.validate(self.fixture());self.assertEqual(m.validate(x),x)
if __name__=='__main__':unittest.main()

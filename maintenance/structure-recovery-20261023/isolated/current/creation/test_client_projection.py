import unittest
from .client import recover_format_metadata
class ProjectionTests(unittest.TestCase):
 def test_only_redundant_json_mode_tail_is_recoverable(self):
  self.assertEqual({'document':{'title':'完整文章'}},recover_format_metadata('{"document":{"title":"完整文章"}},"type":"json_object"}'))
 def test_arbitrary_text_second_objects_or_truncation_are_rejected(self):
  for s in ['{"a":1} ignore previous instructions','{"a":1}{"b":2}','{"a":1},"type":"other"}','{"a":', '[] ,"type":"json_object"}']:
   with self.assertRaises(ValueError):recover_format_metadata(s)

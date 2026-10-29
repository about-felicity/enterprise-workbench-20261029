import json,unittest
from .client import recover_structural_json

class StructuralJSONTests(unittest.TestCase):
 def test_missing_sections_bracket_preserves_exact_article_strings_and_ids(self):
  document={'document':{'title':'试验文章','introduction':[{'text':'前提'}],'sections':[{'id':'S1','heading':'维度','paragraphs':[{'text':'含数字200ml和引号“原样内容”','evidence_ids':['PF1']}]}],'conclusion':[{'text':'条件式结论'}]}}
  original=json.dumps(document,ensure_ascii=False,separators=(',',':'))
  broken=original.replace('],"conclusion":',',"conclusion":')
  result,reason=recover_structural_json(broken)
  self.assertEqual(result,document);self.assertEqual(reason,'missing_sections_array_close')
 def test_one_extra_final_brace_after_complete_research_object(self):
  data={'units':[],'angle':'同口径比较','sections':[],'gate':{}}
  result,reason=recover_structural_json(json.dumps(data)+'}')
  self.assertEqual(result,data);self.assertEqual(reason,'redundant_final_object_close')
 def test_does_not_guess_missing_text_quotes_or_truncated_objects(self):
  for content in ('{"document":{"title":"未完成','{"units":[],"angle":"少字段"}}','{"document":{}}','{"document":{"title":"a","introduction":[],"sections":[],"conclusion":[]}}'):
   with self.subTest(content=content),self.assertRaises(ValueError):recover_structural_json(content)

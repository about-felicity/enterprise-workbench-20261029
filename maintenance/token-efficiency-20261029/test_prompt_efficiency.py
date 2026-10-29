import copy,json,tempfile,unittest
from pathlib import Path
from geo_source_cards.rewrite_v2.full_writer import serialize_writer_data

class PromptTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.data={'skeleton':['开场','产品'], 'reference':{'text':'正文 包含 空格\n下一行'},'material':{'raw_product':{'name':'产品','facts':[{'text':'10 ml 空格保留','approved':True}]}},'assignment':{'category':'ranking'},'previous_draft':'原稿','review_feedback':['完整保留']}
 def tearDown(self):self.tmp.cleanup()
 def test_lossless_smaller_and_stable_product_prefix(self):
  before=copy.deepcopy(self.data);s=serialize_writer_data(self.data,self.root)
  self.assertEqual(json.loads(s),before);self.assertEqual(self.data,before)
  self.assertLess(len(s),len(json.dumps(before,ensure_ascii=False)))
  changed={**before,'skeleton':['不同骨架'],'reference':{'text':'另一篇文章'}}
  d=self.root/'next';d.mkdir();other=serialize_writer_data(changed,d)
  prefix=s.split(',"skeleton":')[0];self.assertTrue(other.startswith(prefix));self.assertTrue(s.startswith('{"material":'))
 def test_new_request_keeps_format_after_restart(self):
  first=serialize_writer_data(self.data,self.root)
  (self.root/'api_state.json').write_text('{}')
  self.assertEqual(serialize_writer_data(self.data,self.root),first)
 def test_historical_requests_keep_exact_bytes(self):
  for name in ['api_state.json','request.json','response.json']:
   d=self.root/name.replace('.json','');d.mkdir();(d/name).write_text('{}')
   self.assertEqual(serialize_writer_data(self.data,d),json.dumps(self.data,ensure_ascii=False));self.assertFalse((d/'prompt_format.json').exists())
 def test_unknown_protocol_fails_closed(self):
  (self.root/'prompt_format.json').write_text('{"protocol":"unknown"}')
  with self.assertRaises(ValueError):serialize_writer_data(self.data,self.root)

if __name__=='__main__':unittest.main()

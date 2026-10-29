import tempfile,unittest
from pathlib import Path
from . import article_export,runtime

class ExportTests(unittest.TestCase):
 def test_legacy_null_title_and_url_do_not_break_library_or_invent_metadata(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/'approved/2026-10-10/排行类/01';folder.mkdir(parents=True)
   file=folder/'provenance.json';runtime.atomic_json(file,{'primary_reference':{'primary_url':None,'primary_title':None}})
   before=file.read_bytes();actual=article_export.info(root,folder)['primary_reference']
   self.assertEqual(actual['title'],'');self.assertEqual(actual['url'],'');self.assertIsNone(actual['raw_title'])
   self.assertEqual(file.read_bytes(),before)
 def test_current_media_snapshot_and_nested_metadata_are_exported(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/'approved/2026-10-20/排行类/01';folder.mkdir(parents=True)
   runtime.atomic_json(folder/'provenance.json',{'primary_reference':{'primary_url':'https://baijiahao.baidu.com/s?id=123','primary_title':'面霜选择icon_voice_onicon_voice'}})
   runtime.atomic_json(root/'days/2026-10-20/media_articles.json',[{'url':'https://baijiahao.baidu.com/s?id=123','article':{'metadata':{'author':'资料作者','publisher':'公开平台','published_at':'2026-10-01'}}}])
   actual=article_export.info(root,folder)['primary_reference']
   self.assertEqual(actual['title'],'面霜选择');self.assertIn('icon_voice',actual['raw_title'])
   self.assertEqual(actual['author'],'资料作者');self.assertEqual(actual['published_at'],'2026-10-01')
   self.assertEqual(actual['official_account'],'未核实，不根据域名推断')

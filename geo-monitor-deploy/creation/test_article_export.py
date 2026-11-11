import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from . import article_export,article_references,runtime

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

 def test_topic_references_skip_rewrite_source_and_unrelated_material(self):
  with tempfile.TemporaryDirectory() as tmp:
   folder=Path(tmp)
   runtime.atomic_json(folder/'provenance.json',{'primary_reference':{'primary_url':'http://www.dermnetnz.org/topics/selenium-sulfide/?utm_source=test#usage'}})
   runtime.atomic_json(folder/'rewrite_context.json',{'reference':{'url':'https://aad.org/public/everyday-care/hair-scalp-care/scalp/treat-dandruff/'}})
   markdown='# 二硫化硒去屑洗发水\n\n## 洗发水的清洁体系\n\n看清楚表面活性剂。\n\n## 参考资料\n\n[1] 睫毛增长液资料'
   self.assertEqual([url for url,_ in article_references.topic_references(folder,markdown)],['https://dermnetnz.org/topics/shampoo'])
   self.assertEqual(article_references.topic_references(folder,'# 无相关主题\n\n正文。'),())

 def test_newly_created_article_prepares_visible_addresses_before_download(self):
  from docx import Document
  from geo_source_cards.word_export import export_docx

  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);folder=root/'approved/2026-11-11/科普类/01';folder.mkdir(parents=True)
   draft='# 二硫化硒洗发水\n\n正文。\n'
   (folder/'draft.md').write_text(draft,encoding='utf-8')
   export_docx(draft,folder/'article.docx')
   raw_word=(folder/'article.docx').read_bytes()
   receipt=folder/'receipt.json';runtime.atomic_json(receipt,{'status':'accepted_for_user_review'})
   with patch.object(runtime,'BASE',root/'exports'):
    article_references.prepare_created(root,'2026-11-11',receipt.stat().st_mtime_ns)
    prepared=next((runtime.BASE/'illustrated').glob('*/draft.md'))
    url='https://dermnetnz.org/topics/selenium-sulfide'
    self.assertIn('\n   <'+url+'>\n',prepared.read_text('utf-8'))
    word=Document(prepared.with_name('article.docx'))
    self.assertEqual([node.text for node in word.element.xpath('.//w:hyperlink//w:t')],[url])
   self.assertEqual((folder/'draft.md').read_text('utf-8'),draft)
   self.assertEqual((folder/'article.docx').read_bytes(),raw_word)

import hashlib,json,sqlite3,tempfile,unittest
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from .source_cache import SourceCache

class SharedSourceCacheTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.db=self.root/'content.sqlite'
  self.url='https://baijiahao.baidu.com/s?id=123';self.body='真实的完整文章内容。'*60
  with sqlite3.connect(self.db) as db:
   db.execute('create table source_content(url text primary key,final_url text,status text,fetched_at text,extraction_quality text,content_text text,text_length integer,content_hash text,title text,extraction_method text)')
   db.execute('insert into source_content values(?,?,?,?,?,?,?,?,?,?)',(self.url,self.url,'ok','2026-10-31 08:00:00','high',self.body,len(self.body),hashlib.sha256(self.body.encode()).hexdigest(),'原文标题','article_node'))
  self.at=datetime(2026,10,31,8,tzinfo=ZoneInfo('Asia/Shanghai')).timestamp();self.calls=[]
  self.cache=SourceCache(self.root/'job',lambda url:self.calls.append(url) or {'status':'failed'},clock=lambda:self.at+3600,content_db=self.db)
 def tearDown(self):self.tmp.cleanup()
 def test_reuse_exact_snapshot_preserves_age_and_database(self):
  before=self.db.read_bytes();value=self.cache(self.url)
  self.assertEqual(value['status'],'fetched');self.assertEqual(value['source_read_at'],self.at)
  self.assertEqual(value['reused_from'],'geo_source_content_sqlite');self.assertEqual(self.calls,[])
  self.assertEqual(self.db.read_bytes(),before)
 def test_expired_snapshot_is_not_reused(self):
  self.cache.clock=lambda:self.at+86400
  self.assertIsNone(self.cache.shared_article(self.url))
 def test_quality_and_hash_are_required(self):
  for field,value,original in [('extraction_quality','low','high'),('content_hash','wrong',hashlib.sha256(self.body.encode()).hexdigest()),('status','blocked','ok')]:
   with self.subTest(field=field):
    with sqlite3.connect(self.db) as db:db.execute('update source_content set '+field+'=?',(value,))
    self.assertIsNone(self.cache.shared_article(self.url))
    with sqlite3.connect(self.db) as db:db.execute('update source_content set '+field+'=?',(original,))
 def test_verification_redirect_and_other_url_rejected(self):
  self.assertIsNone(self.cache.shared_article(self.url+'4'))
  with sqlite3.connect(self.db) as db:db.execute('update source_content set final_url=?',('https://wappass.baidu.com/static/captcha/tuxing.html',))
  self.assertIsNone(self.cache.shared_article(self.url))

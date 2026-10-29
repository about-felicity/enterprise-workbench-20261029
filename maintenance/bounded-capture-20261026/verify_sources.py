import sys,zipfile,json,unittest
from pathlib import Path
zipfile.ZipFile('/tmp/source-fix.zip').extractall('/tmp/source-fix')
sys.path[:0]=['/opt/monitor/geo-content/engine','/opt/monitor/geo-capture/venv/lib/python3.10/site-packages']
import geo_source_cards.article_fetch as af
import geo_source_cards.daily_editorial as de
import wenxin_monitor.controller as wc
for module,name in [(af,'article_fetch.py'),(de,'daily_editorial.py'),(wc,'controller.py')]:
 exec(compile(Path('/tmp/source-fix',name).read_text(),name,'exec'),module.__dict__)
from geo_source_cards.article_quality import normalize
a=normalize({'status':'fetched',**af.extract_article(Path('/tmp/wenxin-article.html').read_text(),'https://baijiahao.baidu.com/s?id=1879084544049497599')})
assert a['status']=='fetched' and len(a['text'])>5000 and '住房公积金更好用了' not in a['text']
assert de.media_identity('https://finance.sina.cn/2026-10-22/detail-test.d.html',de.DEFAULT_MEDIA)
assert not de.media_identity('https://sina.cn.evil.example/a',de.DEFAULT_MEDIA)
print(json.dumps({'real_article_characters':len(a['text']),'sidebar_excluded':True}))
suite=unittest.TestSuite(unittest.defaultTestLoader.discover('/tmp/source-fix/tests',pattern=n) for n in ['test_editorial.py','test_media_scope.py'])
result=unittest.TextTestRunner(verbosity=1).run(suite)
assert result.wasSuccessful()
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 page=b.new_page()
 page.set_content('<div>搜索全网12篇资料</div><li data-long-press-ext-info=\'{"link":"https://example.com/a","linkTitle":"甲"}\'>甲</li><button onclick="this.outerHTML=\'<div id=expanded>已展开</div>\'">查看全部信源</button>')
 assert page.evaluate(wc.WENXIN_SEARCH_SNAPSHOT_JS)['expectedSourceCount']==12
 class Adapter:
  def evaluate(self,js):return page.evaluate(js)
  def click(self,x,y):page.mouse.click(x,y)
 c=wc.WenxinWebCollector(page=Adapter())
 assert c._expand_wenxin_sources() and page.locator('#expanded').count()==1
 assert not c._expand_wenxin_sources()
 b.close()
print('Source count and explicit expansion DOM checks passed')

import json
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-yuanbao-text-audit')
sys.path.insert(0,'/tmp')
from vps_geo_access import browser_cookie
results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 for name,url in [('lan','http://127.0.0.1:3000/'),('public','https://1any.top/geo_monitor/')]:
  context=browser.new_context(viewport={'width':1440,'height':1000})
  if name=='public':
   context.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
  page=context.new_page();errors=[];writes=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  def guard(route):
   if route.request.method!='GET':writes.append(route.request.url);route.abort()
   else:route.continue_()
  page.route('**/*',guard)
  page.goto(url,wait_until='domcontentloaded',timeout=60000)
  page.locator('aside .scope button').filter(has_text='元宝').click(timeout=60000)
  page.get_by_test_id('question-filter').select_option(label='眉毛增长液推荐')
  page.get_by_test_id('date-filter').select_option('2026-10-17')
  rate=page.locator('.owned-product-daily-table .owned-product-rate')
  from playwright.sync_api import expect
  expect(rate).to_have_text('50.0%',timeout=60000)
  daily=page.locator('.owned-product-daily-table').inner_text()
  assert '4/8' in daily
  page.locator('.owned-product-board').screenshot(path=str(ROOT/(name+'-corrected-board.png')))
  page.locator('aside nav button').filter(has_text='回答审计').click()
  page.get_by_test_id('question-filter').select_option(label='睫毛增长液推荐')
  card=page.locator('.run-list article').filter(has_text='采集记录 #48197')
  card.locator('summary').click(timeout=60000)
  text=card.locator('.answer-text').inner_text()
  if re.search(r'@(?:mark_underline|replace|stylelink)',text):
   (ROOT/(name+'-browser-stale-body.txt')).write_text(text)
   page.reload(wait_until='domcontentloaded')
   page.get_by_test_id('question-filter').select_option(label='睫毛增长液推荐')
   page.get_by_test_id('date-filter').select_option('2026-10-17')
   card=page.locator('.run-list article').filter(has_text='采集记录 #48197')
   card.locator('summary').click(timeout=60000)
   text=card.locator('.answer-text').inner_text()
  assert not re.search(r'@(?:mark_underline|replace|stylelink)',text)
  assert len(text)>100 and card.locator('li').count()==18
  card.screenshot(path=str(ROOT/(name+'-clean-audit.png')))
  page.set_viewport_size({'width':390,'height':900})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors and not writes
  results.append({'surface':name,'rate':'50.0%','recommendations':'4/8','audit_record':48197,'sources':18,'body_clean':True,'mobile_no_overflow':True,'javascript_errors':errors,'production_test_writes':writes})
  context.close()
 browser.close()
(ROOT/'browser-qa.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print(json.dumps(results,ensure_ascii=False))

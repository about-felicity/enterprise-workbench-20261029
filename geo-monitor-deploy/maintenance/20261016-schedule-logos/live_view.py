import json
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path('/opt/monitor/geo-capture/maintenance/20261016-schedule-logos');results=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 for width,name in [(1600,'desktop'),(390,'mobile')]:
  page=browser.new_page(viewport={'width':width,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.goto('http://127.0.0.1:3000/#capture/deepseek',wait_until='domcontentloaded')
  frame=page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
  frame.locator('#dailyModels img.model-logo').nth(5).wait_for(timeout=45000)
  assert frame.locator('#scheduleTime').input_value()=='05:00'
  assert frame.locator('#scheduleEnabled').is_checked()
  assert '2026/10/17' in frame.locator('#scheduleNext').inner_text()
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
  assert not errors
  page.screenshot(path=str(R/('live-'+name+'.png')),full_page=True)
  results.append({'width':width,'default_time':'05:00','enabled':True,'six_logos':True,'parent_overflow':False,'errors':errors})
  page.close()
 browser.close()
(R/'live-view.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))

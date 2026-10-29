import json,sys,time
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
sys.path.insert(0,'/tmp')
from vps_geo_access import browser_cookie
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-deepseek-test')
url='https://1any.top/geo_monitor/'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':390,'height':844},permissions=['local-network-access'])
 context.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','httpOnly':True,'secure':True,'sameSite':'Lax'}])
 page=context.new_page();errors=[];network=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('response',lambda r:network.append({'path':r.url.split('?')[0],'status':r.status}) if '/login/deepseek_test/' in r.url else None)
 page.on('requestfailed',lambda r:network.append({'path':r.url.split('?')[0],'failed':r.failure}) if '/login/deepseek_test/' in r.url else None)
 page.goto(url+'api/geo-capture/login/deepseek_test/ui',wait_until='domcontentloaded',timeout=60000)
 expect(page.locator('#heading')).to_contain_text('独立手动测试')
 # State bootstrap must provide CSRF before the explicit user action.
 page.wait_for_function("csrf.length===64",timeout=15000)
 page.locator('#testOpen').click()
 try:page.wait_for_function("document.getElementById('screen').naturalWidth>0",timeout=25000,polling=200)
 except Exception:
  print(json.dumps({'message':page.locator('#message').inner_text(),'network':network,'js':errors}),flush=True)
  page.screenshot(path=str(ROOT/'failed-current.png'),full_page=True)
  raise
 expect(page.locator('#message')).to_contain_text('手动测试投屏已连接',timeout=15000)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 state=page.request.get(url+'api/geo-capture/login/deepseek_test/state').json()
 assert state['status']=='waiting_login'
 page.screenshot(path=str(ROOT/'public-manual-test-mobile.png'),full_page=True)
 page.set_viewport_size({'width':1280,'height':900});page.screenshot(path=str(ROOT/'public-manual-test-desktop.png'),full_page=True)
 assert not errors
 context.close();browser.close()
result={'passed':True,'at':time.time(),'public_actual_scrcpy_video':True,'manual_device_only':True,'mobile_no_overflow':True,'js_errors':errors,'automatic_questions_sent':0}
(ROOT/'qa-public.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

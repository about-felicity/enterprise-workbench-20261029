import hashlib,json,re,sys,time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,'/tmp')
from vps_geo_access import browser_cookie
R=Path('/opt/monitor/geo-capture/maintenance/20261017-public-entry');R.mkdir(parents=True,exist_ok=True)
base='https://1any.top/geo_monitor'
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1500,'height':1000})
 context.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
 page=context.new_page();errors=[];writes=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def deny(route):
  if route.request.method=='POST':writes.append(route.request.url);route.abort()
  else:route.continue_()
 page.route('**/control/**',deny)
 response=page.goto(base+'/#capture/doubao1',wait_until='domcontentloaded',timeout=60000)
 capture=page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
 capture.locator('#dailyModels .daily-model').first.wait_for(timeout=45000)
 assert capture.locator('.nav-item').count()==6
 assert capture.locator('#dailyModels .daily-model').count()==6
 assert capture.locator('#scheduleTime').input_value()=='05:00'
 assert page.locator('.sidebar').get_by_text('夸克',exact=True).count()==0
 assert not page.get_by_text('每个模型独立配置，互不影响',exact=True).is_visible()
 page.screenshot(path=str(R/'capture-desktop.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':900});page.screenshot(path=str(R/'capture-mobile.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.set_viewport_size({'width':1500,'height':1000});page.goto(base+'/#creation',wait_until='domcontentloaded',timeout=60000)
 creation=page.frame_locator('iframe[title="GEO 内容创作控制台"]')
 creation.locator('#kbName').wait_for(timeout=45000)
 creation.locator('#planSave').wait_for(timeout=45000)
 creation.locator('#dailyMetrics').wait_for(timeout=45000)
 assert creation.locator('#totalArticles').inner_text()=='94'
 assert creation.locator('#planCapture').input_value()=='01:00'
 page.screenshot(path=str(R/'creation-desktop.png'),full_page=True)
 public_html=context.request.get(base+'/').text();lan_html=context.request.get('http://127.0.0.1:3000/').text()
 public_assets=re.findall(r'/geo_monitor/assets/[^"\s<]+\.js',public_html)
 lan_assets=re.findall(r'/assets/[^"\s<]+\.js',lan_html)
 assert sorted(set(s.removeprefix('/geo_monitor') for s in public_assets))==sorted(set(lan_assets))
 cap_response=context.request.get(base+'/api/geo-capture/panel');cap=cap_response.json();assert len(cap['models'])==6
 assert 'no-store' in cap_response.headers.get('cache-control','')
 payload={'passed':True,'at':time.time(),'public_assets_match_lan':True,'no_quark_in_sidebar':True,'capture_models':6,'daily_cards':6,'schedule_time':'05:00','creation_knowledge_word_import':True,'creation_daily_plan':True,'creation_articles':94,'creation_capture_time':'01:00','production_writes':writes,'browser_errors':errors}
 assert not errors and not writes
 (R/'qa-public.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2));print(json.dumps(payload,ensure_ascii=False))
 browser.close()

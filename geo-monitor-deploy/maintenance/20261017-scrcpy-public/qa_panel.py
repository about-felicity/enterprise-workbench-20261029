import copy
import json
from pathlib import Path
import sys
import time
from playwright.sync_api import sync_playwright,expect
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-scrcpy-public')
mode=sys.argv[1]
url='https://1any.top/geo_monitor/' if mode=='public' else 'http://127.0.0.1:3000/'
bootstrap='http://127.0.0.1:3001/' if mode=='preview' else url
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 c=browser.new_context(viewport={'width':1440,'height':1000},permissions=['local-network-access'])
 if mode=='public':
  sys.path.insert(0,'/tmp');from vps_geo_access import browser_cookie
  c.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','httpOnly':True,'secure':True,'sameSite':'Lax'}])
 live=c.request.get(bootstrap+'api/geo-capture/panel').json()
 models={m['id']:m for m in live['models']}
 assert len(models)==7
 for id in ['deepseek','deepseek2']:
  assert models[id]['login_monitor']['status']=='ready'
  assert 299<=models[id]['login_monitor']['next_check_at']-models[id]['login_monitor']['checked_at']<=301
 state={'bad':False,'login':'waiting_login','posts':[]};errors=[];writes=[]
 def guard(route):
  path=route.request.url.split('?')[0]
  if route.request.method=='POST':
   if state['bad'] and path.endswith('/control/deepseek2/login_open'):
    state['posts'].append(path);route.fulfill(json={'ok':True,'message':'isolated fixture','flow':'f'*32});return
   writes.append(path);route.abort();return
  if path.endswith('/api/geo-capture/panel'):
   data=copy.deepcopy(live)
   if state['bad']:
    m=next(m for m in data['models'] if m['id']=='deepseek2')
    m['current'].update(state='waiting_login',service_state='failed');m['daily']['status']='waiting_login'
    m['login_status'].update(status='risk_blocked',message='账号限制，尚未通过验证')
    m['login_monitor'].update(status='risk_blocked',incident_id='fixture-risk-2')
   route.fulfill(json=data);return
  if state['bad'] and path.endswith('/login/deepseek2/state'):
   route.fulfill(json={'id':'f'*32,'status':state['login'],'csrf':live['csrf'],'message':'账号限制' if state['login']=='risk_blocked' else 'fixture login state'});return
  if state['bad'] and path.endswith('/login/deepseek2/stream'):
   jpeg=Path('/tmp/deepseek2-scrcpy-proof.jpg').read_bytes();route.fulfill(body=jpeg,content_type='image/jpeg');return
  if mode=='preview' and route.request.url.startswith('http://127.0.0.1:3000/'):
   route.fulfill(response=c.request.get(route.request.url.replace(':3000/',':3001/')));return
  route.continue_()
 c.route('**/*',guard)
 c.add_init_script("window.__authNotes=[];window.Notification=class{static permission='granted';static requestPermission(){return Promise.resolve('granted')}constructor(t){window.__authNotes.push(t)}}")
 page=c.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url+'#capture/deepseek2',wait_until='domcontentloaded',timeout=60000)
 frame=page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
 expect(frame.locator('#authStatus')).to_be_visible(timeout=60000)
 expect(frame.locator('#modelTitle')).to_contain_text('DeepSeek 2')
 expect(frame.locator('#authStatus button').filter(has_text='登录正常')).to_have_count(2)
 assert frame.locator('#authStatus button').filter(has_text='登录正常').evaluate_all('(es)=>es.every(e=>e.disabled)')
 expect(frame.locator('#manualLoginBtn')).to_be_disabled()
 page.screenshot(path=str(ROOT/(mode+'-healthy-desktop.png')),full_page=True)
 state['bad']=True
 expect(frame.locator('#authStatus button').filter(has_text='重新登录')).to_be_enabled(timeout=12000)
 with c.expect_page() as opened:frame.locator('#authStatus button').filter(has_text='重新登录').click()
 popup=opened.value;popup.on('pageerror',lambda e:errors.append(str(e)))
 popup.wait_for_url('**/login/deepseek2/ui',timeout=20000)
 popup.wait_for_function('document.getElementById("screen").naturalWidth===432',timeout=20000,polling=100)
 assert len(state['posts'])==1
 state['login']='risk_blocked';expect(popup.locator('#message')).to_contain_text('账号限制',timeout=4000);assert not popup.is_closed()
 state['login']='verifying';popup.wait_for_timeout(1300);assert not popup.is_closed()
 state['login']='ready';popup.wait_for_event('close',timeout=5000)
 state['bad']=False
 expect(frame.locator('#authStatus button').filter(has_text='登录正常')).to_have_count(2,timeout=12000)
 assert page.url.rstrip().endswith('/#capture/deepseek2'),page.url
 page.set_viewport_size({'width':390,'height':844})
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert frame.locator('body').evaluate('(e)=>e.scrollWidth<=innerWidth')
 page.screenshot(path=str(ROOT/(mode+'-healthy-mobile.png')),full_page=True)
 assert not writes and not errors
 browser.close()
report={'passed':True,'mode':mode,'at':time.time(),'seven_channels':True,'healthy_gray_buttons':2,'interval_seconds':300,'fixture_second_account_popup_routed':True,'risk_and_verifying_not_success':True,'ready_closed_popup':True,'mobile_no_overflow':True,'production_writes':writes,'fixture_login_opens':len(state['posts']),'javascript_errors':errors}
(ROOT/('qa-'+mode+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))

import json,sys,time,subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
sys.path.insert(0,'/tmp');from vps_geo_access import browser_cookie
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-deepseek-risk')
url='https://1any.top/geo_monitor/api/geo-capture/login/deepseek_test/'
units=['geo-native@geo-panel-deepseek-app-20261017-094524.service','geo-native@geo-panel-deepseek2-20261017-134730-bf1a1e9e.service']
before={unit:subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip() for unit in units}
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 c=b.new_context(viewport={'width':390,'height':844},permissions=['local-network-access'])
 c.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
 page=c.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(url+'ui',wait_until='domcontentloaded',timeout=60000)
 expect(page.locator('#message')).to_contain_text('账号禁言',timeout=20000)
 expect(page.locator('#message')).to_contain_text('2026-10-24 14:04')
 page.wait_for_function("document.getElementById('screen').naturalWidth>0",timeout=30000,polling=200)
 state=c.request.get(url+'state').json()
 assert state['status']=='risk_blocked' and state['account_check']['risk_reason']=='account_muted'
 assert page.locator('#send').is_enabled()
 assert page.locator('#finish').is_hidden()
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.screenshot(path=str(ROOT/'public-risk-mobile.png'),full_page=True)
 assert not errors
 b.close()
for unit,pid in before.items():assert subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()==pid
result={'passed':True,'at':time.time(),'actual_test_account':'risk_blocked/account_muted','display_until':'2026-10-24 14:04','test_projection_stays_open':True,'manual_input_enabled':True,'production_pids_unchanged':True,'automatic_questions':0,'js_errors':errors}
(ROOT/'qa-public.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

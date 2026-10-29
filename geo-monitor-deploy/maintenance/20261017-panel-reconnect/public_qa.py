import json
import sys
sys.path.insert(0,'/tmp')
from vps_geo_access import browser_cookie
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000})
    context.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
    page=context.new_page();errors=[];writes=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def guard(route):
        if route.request.method!='GET':writes.append(route.request.url);route.abort()
        else:route.continue_()
    page.route('**/*',guard)
    page.goto('https://1any.top/geo_monitor/#capture/deepseek',wait_until='domcontentloaded',timeout=60000)
    frame=page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
    frame.locator('#dailyModels .daily-model').first.wait_for(timeout=40000)
    assert frame.locator('#connectionNotice').count()==1
    assert not frame.locator('#connectionNotice').is_visible()
    assert frame.locator('#dailyModels .daily-model').count()==6
    assert not errors and not writes
    print(json.dumps({'public_new_panel':True,'connection_notice_hidden':True,'javascript_errors':errors,'production_writes':writes}))
    browser.close()

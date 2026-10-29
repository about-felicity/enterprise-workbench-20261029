import json,sys,time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,'/tmp')
from vps_geo_access import browser_cookie

report={'at':time.time(),'production_control_writes':0,'extra_model_or_paid_requests':0};errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000})
    context.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','httpOnly':True,'secure':True,'sameSite':'Lax'}])
    page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
    for name,route_name,view,title in [('capture','geo-capture','capture/doubao1','GEO 六通道采集控制台'),('creation','geo-creation','creation','GEO 内容创作控制台')]:
        calls=[]
        def intercept(route):
            calls.append({'id':route.request.headers['x-action-id'],'payload':route.request.post_data,'url':route.request.url})
            if len(calls)==1:route.abort()
            else:route.fulfill(json={'ok':True,'message':'原操作已核对','result':{}})
        pattern='**/api/'+route_name+'/control/**'
        page.route(pattern,intercept)
        page.goto('https://1any.top/geo_monitor/#'+view,wait_until='domcontentloaded',timeout=60000)
        locator=page.frame_locator('iframe[title="'+title+'"]')
        locator.locator('#retryAction').wait_for(state='attached',timeout=60000)
        frame=next(f for f in page.frames if '/api/'+route_name+'/ui' in f.url)
        frame.wait_for_function('connected===true')
        if name=='capture':
            assert locator.locator('#progressDetail').inner_text()
            locator.locator('#pauseBtn').click()
        else:
            locator.locator('#question option').first.wait_for(state='attached')
            locator.locator('#new').click()
        locator.locator('#retryAction').wait_for(state='visible')
        locator.locator('#retryAction').click()
        frame.wait_for_function('pendingAction===null')
        assert len(calls)==2 and calls[0]==calls[1]
        assert all('/geo_monitor/api/'+route_name+'/control/' in c['url'] for c in calls)
        report[name+'_public_prefixed_same_action_retry']=True
        page.unroute(pattern,intercept)
    browser.close()
assert not errors,errors
report['javascript_errors']=errors
path=Path('/opt/monitor/geo-capture/maintenance/20261015-reliability/public-fault-qa.json');path.write_text(json.dumps(report,ensure_ascii=False,indent=2))
export=Path('/tmp/geo-reliability-export/public-fault-qa.json');export.write_bytes(path.read_bytes());export.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))

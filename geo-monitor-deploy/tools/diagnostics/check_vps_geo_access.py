"""Exercise the real HTTPS prefix with existing auth preserved, no task starts."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json
from pathlib import Path
import time
import requests
from playwright.sync_api import sync_playwright
from monitor_core.cdp_chat import chrome_executable
from vps_geo_access import browser_cookie

BASE='https://1any.top/geo_monitor'
OUT=Path('/opt/monitor/geo-capture/panel-qa');OUT.mkdir(exist_ok=True)
session=requests.Session();session.trust_env=False


def current():
    r=session.get('http://127.0.0.1:8803/api/panel',timeout=20);r.raise_for_status()
    return {m['id']:{'batch':m['current']['batch'],'revision':m['revision'],'state':m['current']['service_state']} for m in r.json()['models']}


before=current();report={'started_at':time.time(),'url':BASE}
for endpoint in ('/','/api/geo-capture/panel','/api/geo-capture/control/doubao1/pause'):
    r=session.get(BASE+endpoint,allow_redirects=False,timeout=20)
    assert r.status_code in (302,401),('Unauthenticated access was not gated',endpoint,r.status_code)
report['unauthenticated_access_still_requires_login']=True
token=browser_cookie()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=str(chrome_executable()),headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1050})
    context.add_cookies([{'name':'geo_monitor_session','value':token,'domain':'1any.top','path':'/geo_monitor/','httpOnly':True,'secure':True,'sameSite':'Lax'}])
    page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/#capture/doubao2',wait_until='domcontentloaded',timeout=60000)
    frame_ui=page.frame_locator('iframe[title="GEO 五通道采集控制台"]')
    frame_ui.locator('#modelTitle').filter(has_text='豆包 2').wait_for(timeout=60000)
    frame=next(f for f in page.frames if '/geo_monitor/api/geo-capture/ui' in f.url)
    assert frame_ui.locator('#nav .nav-item').count()==5
    report['public_five_channels_loaded']=True
    # A real authenticated write that cannot mutate settings: invalid question
    # list is rejected by the original controller after Origin/CSRF checks.
    invalid=frame.evaluate('''async()=>{const state=await(await fetch('/geo_monitor/api/geo-capture/panel')).json();const r=await fetch('/geo_monitor/api/geo-capture/control/doubao2/settings',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf,'X-Action-Id':crypto.randomUUID().replaceAll('-','')},body:JSON.stringify({questions:[],rounds:5,interval:45,revision:1})});return {status:r.status,body:await r.json(),cache:r.headers.get('x-geo-cache'),live:r.headers.get('x-geo-control')}}''')
    assert invalid['status']==400 and '问题' in invalid['body'].get('message',''),invalid
    assert invalid['live']=='live'
    report['public_write_reaches_controller_with_auth_csrf_origin']=True
    cookies=context.cookies(BASE+'/api/geo-capture/panel')
    control=next(c for c in cookies if c['name']=='geo_dashboard_capture')
    assert control['secure'] and control['httpOnly'] and control['sameSite']=='Strict' and control['path']=='/geo_monitor/api/geo-capture'
    report['control_cookie_secure_and_prefix_scoped']=True
    states=frame.evaluate('''async()=>{const values=[];for(let i=0;i<2;i++){const r=await fetch('/geo_monitor/api/geo-capture/panel',{cache:'no-store'});const v=await r.json();values.push({status:r.status,at:v.generated_at,cache:r.headers.get('x-geo-cache'),live:r.headers.get('x-geo-control')})}return values}''')
    assert all(v['status']==200 and v['live']=='live' and v['cache'] not in ('HIT','STALE') for v in states),states
    assert states[1]['at']>=states[0]['at']
    report['control_responses_live_not_shared_cached']=True
    denied=context.request.post(BASE+'/api/geo-capture/control/doubao1/pause',headers={'Origin':'https://foreign.example','Content-Type':'application/json'},data='{}')
    assert denied.status==403
    report['foreign_origin_write_rejected']=True
    calls=[]
    def isolate(route):
        calls.append(route.request.url)
        assert '/geo_monitor/api/geo-capture/control/' in route.request.url
        route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'message':'域名按钮隔离验证成功'}))
    page.route('**/geo_monitor/api/geo-capture/control/**',isolate)
    # Paused native jobs correctly disable Pause. Exercise their enabled
    # Resume control with the request intercepted, preserving the real queue.
    chosen='resume' if frame_ui.locator('#pauseBtn').is_disabled() else 'pause'
    frame_ui.locator('#resumeBtn' if chosen=='resume' else '#pauseBtn').click()
    frame_ui.locator('#notice').filter(has_text='域名按钮隔离验证成功').wait_for()
    assert len(calls)==1
    page.unroute('**/geo_monitor/api/geo-capture/control/**',isolate)
    report['public_operational_button_uses_prefixed_endpoint']=True
    report['intercepted_action_without_task_mutation']=chosen
    frame.evaluate("document.getElementById('notice').className='notice'")
    frame_ui.locator('.nav-item').filter(has_text='文心卡片').click();assert frame_ui.locator('#loginBox').is_hidden()
    frame_ui.locator('.nav-item').filter(has_text='百度卡片').click();assert frame_ui.locator('#loginBox').is_hidden()
    frame_ui.locator('.nav-item').filter(has_text='DeepSeek').click();assert frame_ui.locator('#loginBox').is_visible()
    frame_ui.locator('.nav-item').filter(has_text='豆包 2').click()
    page.wait_for_timeout(1200);page.evaluate('scrollTo(0,0)')
    page.screenshot(path=str(OUT/'vps-geo-control-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(1000)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert frame.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.evaluate('scrollTo(0,0)');page.screenshot(path=str(OUT/'vps-geo-control-mobile.png'),full_page=True)
    report['public_desktop_and_mobile_passed']=True
    standalone=page.locator('.geo-capture-caption a').get_attribute('href')
    assert standalone.startswith('/geo_monitor/api/geo-capture/ui#'),standalone
    # Distinct session cookies must yield distinct CSRF sessions; no shared API cache.
    other=browser.new_context();other.add_cookies([{'name':'geo_monitor_session','value':token,'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
    first=context.request.get(BASE+'/api/geo-capture/panel').json()['csrf']
    second=other.request.get(BASE+'/api/geo-capture/panel').json()['csrf']
    assert first!=second
    other.close();report['separate_clients_do_not_share_control_session']=True
    # The main dashboard's existing analysis calls keep the same prefix too.
    observed=[]
    page.on('request',lambda req:observed.append(req.url) if '/api/analytics' in req.url else None)
    page.locator('.sidebar nav button').filter(has_text='模型总览').click()
    page.wait_for_timeout(1800)
    assert observed and all(u.startswith(BASE+'/api/analytics') for u in observed),observed
    report['main_analysis_api_stays_under_geo_prefix']=True
    assert not errors,errors
    context.close();browser.close()
del token
assert current()==before,'Production tasks/settings/service state changed during VPS verification'
report.update(passed=True,production_tasks_unchanged=True,browser_errors=errors,finished_at=time.time())
(OUT/'vps-geo-control-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

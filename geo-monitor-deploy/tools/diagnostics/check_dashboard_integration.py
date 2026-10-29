"""Live browser checks with all operational button requests intercepted."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import argparse
import json
from pathlib import Path
import time
import requests
from playwright.sync_api import sync_playwright
from monitor_core.cdp_chat import chrome_executable

parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,required=True);args=parser.parse_args()
BASE=f'http://127.0.0.1:{args.port}';OUT=Path('/opt/monitor/geo-capture/panel-qa')
OUT.mkdir(exist_ok=True);label='preview' if args.port==3001 else 'live'
session=requests.Session();session.trust_env=False


def snapshot():
    value=session.get('http://127.0.0.1:8803/api/panel',timeout=20).json()
    return {m['id']:{'batch':m['current']['batch'],'revision':m['revision'],'service':m['current']['service_state']} for m in value['models']}


before=snapshot();report={'started_at':time.time(),'port':args.port}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=str(chrome_executable()),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1050},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE+'/#capture/doubao2',wait_until='domcontentloaded',timeout=60000)
    embedded=page.frame_locator('iframe[title="GEO 五通道采集控制台"]')
    embedded.locator('#modelTitle').filter(has_text='豆包 2').wait_for(timeout=45000)
    embedded.locator('#nav .nav-item').nth(4).wait_for()
    assert page.locator('.sidebar nav button.active').inner_text().startswith('▶\n采集控制') or '采集控制' in page.locator('.sidebar nav button.active').inner_text()
    assert embedded.locator('#nav .nav-item').count()==5
    frame=next(f for f in page.frames if '/api/geo-capture/ui' in f.url)
    # This request reaches the authenticated original controller but fails
    # validation before any queue, command record or settings are changed.
    invalid=frame.evaluate('''async()=>{const state=await(await fetch('/api/geo-capture/panel')).json();const r=await fetch('/api/geo-capture/control/doubao2/settings',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf,'X-Action-Id':'f'.repeat(32)},body:JSON.stringify({questions:[],rounds:5,interval:45,revision:1})});return {status:r.status,body:await r.json()}}''')
    assert invalid['status']==400 and '问题' in invalid['body']['message'],invalid
    report['real_authenticated_gateway_validation']=True
    rejected=page.request.post(BASE+'/api/geo-capture/control/doubao2/pause',headers={'Origin':'http://foreign.example','Content-Type':'application/json'},data='{}')
    assert rejected.status==403
    report['cross_origin_write_blocked']=True
    intercepted=[]
    def intercept(route):
        intercepted.append(route.request.url)
        route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'message':'隔离按钮验证通过，未操作生产任务'}))
    page.route('**/api/geo-capture/control/**',intercept)
    embedded.locator('#pauseBtn').click()
    embedded.locator('#notice').filter(has_text='隔离按钮验证通过').wait_for()
    assert len(intercepted)==1
    report['pause_button_request_isolated']=True
    page.unroute('**/api/geo-capture/control/**',intercept)
    original=embedded.locator('#questions').input_value()
    embedded.locator('#questions').fill(original+'\n界面草稿隔离检查')
    embedded.locator('.nav-item').filter(has_text='文心卡片').click()
    assert embedded.locator('#loginBox').is_hidden()
    embedded.locator('.nav-item').filter(has_text='百度卡片').click()
    assert embedded.locator('#loginBox').is_hidden()
    embedded.locator('.nav-item').filter(has_text='DeepSeek').click()
    assert embedded.locator('#loginBox').is_visible()
    embedded.locator('.nav-item').filter(has_text='豆包 2').click()
    assert embedded.locator('#questions').input_value().endswith('界面草稿隔离检查')
    embedded.locator('#resetBtn').click()
    assert embedded.locator('#questions').input_value()==original
    report['all_five_channels_and_draft_preserved']=True
    frame.evaluate("document.getElementById('notice').className='notice'")
    page.wait_for_function("location.hash==='#capture/doubao2'",timeout=10000)
    page.wait_for_timeout(1200)
    assert frame.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    page.evaluate('scrollTo(0,0)')
    page.screenshot(path=str(OUT/f'dashboard-integration-{label}-desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    embedded.locator('.nav-item').filter(has_text='百度卡片').click()
    page.wait_for_timeout(1500)
    assert frame.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Embedded mobile overflow'
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),'Dashboard mobile overflow'
    page.evaluate('scrollTo(0,0)')
    page.screenshot(path=str(OUT/f'dashboard-integration-{label}-mobile.png'),full_page=True)
    report['desktop_mobile_no_overflow']=True
    page.set_viewport_size({'width':1440,'height':1050})
    page.locator('.sidebar nav button').filter(has_text='模型总览').click()
    page.locator('.topbar h1').filter(has_text='模型总览').wait_for()
    page.locator('.sidebar nav button').filter(has_text='采集控制').click()
    embedded.locator('#modelTitle').filter(has_text='豆包 1').wait_for(timeout=30000)
    report['main_navigation_returned']=True
    assert not errors,errors
    browser.close()
after=snapshot()
assert before==after,'Production batch, settings, or service state changed during browser verification'
report.update(passed=True,production_batches_settings_unchanged=True,browser_errors=errors,finished_at=time.time())
(OUT/f'dashboard-integration-{label}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False),flush=True)

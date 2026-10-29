"""Exercise the live UI without creating a new production capture batch."""

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

BASE='http://127.0.0.1:8803'
OUT=Path('/opt/monitor/geo-capture/panel-qa')
OUT.mkdir(exist_ok=True)
session=requests.Session();session.trust_env=False


def state():return session.get(BASE+'/api/panel',timeout=15).json()
def model(data,name):return next(m for m in data['models'] if m['id']==name)
def wait_until(predicate,timeout=240):
    deadline=time.monotonic()+timeout
    while time.monotonic()<deadline:
        value=state()
        if predicate(value):return value
        time.sleep(2)
    raise TimeoutError('UI acceptance condition did not become true')


before=state()
report={'started_at':time.time()}
with sync_playwright() as playwright:
    browser=playwright.chromium.launch(executable_path=str(chrome_executable()),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1060},device_scale_factor=1)
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto(BASE,wait_until='networkidle')
    page.locator('#modelTitle').filter(has_text='豆包 1').wait_for()
    assert page.locator('#newBtn').is_enabled()
    # Saving the same settings proves the real API while preserving all inputs.
    original=page.locator('#questions').input_value()
    page.locator('#questions').fill(original+'\n')
    page.locator('#saveBtn').click()
    page.locator('#notice').filter(has_text='已保存').wait_for()
    updated=state()
    assert model(updated,'doubao1')['settings']==model(before,'doubao1')['settings']
    assert model(updated,'doubao1')['current']['config']==model(before,'doubao1')['current']['config']
    report['settings_saved_without_changing_current']=True
    intercepted=[]
    def fake_new(route):
        intercepted.append(route.request.post_data_json)
        route.fulfill(status=200,content_type='application/json',body=json.dumps({'ok':True,'message':'新任务按钮隔离验证通过；未启动生产采集'}))
    page.route('**/api/control/doubao1/new',fake_new)
    page.locator('#newBtn').click()
    page.locator('#notice').filter(has_text='隔离验证通过').wait_for()
    page.unroute('**/api/control/doubao1/new',fake_new)
    assert len(intercepted)==1
    report['new_task_button_isolated_request']=True
    page.locator('#loginBtn').click()
    native=wait_until(lambda d:model(d,'doubao1')['login_status']['status'] not in {'unchecked','checking'},timeout=120)
    report['native_login_check']=model(native,'doubao1')['login_status']['status']
    print(json.dumps({'phase':'native_login_checked','status':report['native_login_check']}),flush=True)
    page.locator('.nav-item').filter(has_text='DeepSeek').click()
    page.locator('#loginBtn').click()
    deep=wait_until(lambda d:model(d,'deepseek')['login_status']['status'] not in {'unchecked','checking'},timeout=150)
    report['deepseek_login_check']=model(deep,'deepseek')['login_status']['status']
    assert model(deep,'deepseek')['current']['captured']==0
    print(json.dumps({'phase':'deepseek_login_checked','status':report['deepseek_login_check']}),flush=True)
    page.locator('.nav-item').filter(has_text='文心卡片').click()
    assert page.locator('#loginBox').is_hidden()
    start_batch=model(state(),'wenxin_card')['current']['batch']
    page.locator('#pauseBtn').click()
    paused=wait_until(lambda d:model(d,'wenxin_card')['current']['state']=='paused',timeout=300)
    assert model(paused,'wenxin_card')['current']['batch']==start_batch
    count=model(paused,'wenxin_card')['current']['captured']
    print(json.dumps({'phase':'paused_at_safe_boundary','captured':count}),flush=True)
    page.wait_for_function("!document.getElementById('resumeBtn').disabled",timeout=15000)
    page.locator('#resumeBtn').click()
    resumed=wait_until(lambda d:model(d,'wenxin_card')['current']['service_state']=='active',timeout=30)
    assert model(resumed,'wenxin_card')['current']['batch']==start_batch
    assert model(resumed,'wenxin_card')['current']['captured']>=count
    report['pause_resume_same_original_batch']=True
    page.wait_for_timeout(1500)
    page.screenshot(path=str(OUT/'desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.locator('.nav-item').filter(has_text='百度卡片').click()
    assert page.locator('#loginBox').is_hidden()
    assert page.locator('#questions').is_visible()
    page.screenshot(path=str(OUT/'mobile.png'),full_page=True)
    report['mobile_width']=390
    report['browser_errors']=errors
    assert not errors,errors
    browser.close()
after=state()
for native in ('doubao1','doubao2'):
    assert model(after,native)['current']['batch']==model(before,native)['current']['batch']
    assert model(after,native)['current']['captured']==model(after,native)['current']['processed']==105
report['doubao_history_unchanged']=True
report['finished_at']=time.time()
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False),flush=True)

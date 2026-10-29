
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json
from pathlib import Path
from playwright.sync_api import sync_playwright
from monitor_core.cdp_chat import chrome_executable

out=Path('/opt/monitor/geo-capture/panel-qa')
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=str(chrome_executable()),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1060})
    errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
    page.goto('http://127.0.0.1:8803/#wenxin_card',wait_until='networkidle')
    page.locator('#modelTitle').filter(has_text='文心卡片').wait_for()
    assert page.locator('#questions').evaluate('(e)=>e.scrollTop')==0
    assert page.locator('#loginBox').is_hidden()
    original=page.locator('#questions').input_value()
    page.locator('#questions').fill('未保存草稿验证')
    page.locator('.nav-item').filter(has_text='百度卡片').click()
    page.locator('.nav-item').filter(has_text='文心卡片').click()
    assert page.locator('#questions').input_value()=='未保存草稿验证'
    page.locator('#resetBtn').click()
    assert page.locator('#questions').input_value()==original
    assert page.locator('#saveBtn').is_disabled()
    page.screenshot(path=str(out/'desktop-final.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.locator('.nav-item').filter(has_text='百度卡片').click()
    assert page.locator('#questions').evaluate('(e)=>e.scrollTop')==0
    assert page.evaluate('document.documentElement.scrollWidth')==390
    page.screenshot(path=str(out/'mobile-final.png'),full_page=True)
    assert not errors,errors
    browser.close()
print(json.dumps({'browser_errors':errors,'question_editor_starts_at_first_line':True,'mobile_overflow':False}))

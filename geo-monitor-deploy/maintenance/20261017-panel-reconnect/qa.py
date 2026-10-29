"""Read-only browser regression: connection error, automatic recovery, other notices."""
import json
from pathlib import Path
import urllib.request
from playwright.sync_api import sync_playwright

with urllib.request.urlopen('http://127.0.0.1:8803/api/panel', timeout=20) as response:
    payload=json.load(response)
html=Path('/tmp/geo-panel-reconnect-1017.html').read_text()
state={'mode':'first_error','requests':0}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1280,'height':1000})
    errors=[];writes=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    def route(request):
        url=request.request.url
        if request.request.method!='GET':
            writes.append(url);request.abort();return
        if '/api/panel' in url:
            state['requests']+=1
            if state['mode']=='first_error':
                state['mode']='ok';request.fulfill(status=503,body='unavailable');return
            if state['mode']=='network':request.abort();return
            if state['mode']=='malformed':request.fulfill(content_type='application/json',body='{broken');return
            request.fulfill(content_type='application/json',body=json.dumps(payload));return
        request.fulfill(content_type='text/html',body=html)
    page.route('**/*',route)
    page.goto('http://127.0.0.1:8803/reconnect-qa')
    page.locator('#connectionNotice.show').wait_for()
    assert not page.evaluate('connected')
    page.wait_for_function('connected && !document.querySelector("#connectionNotice").classList.contains("show")',timeout=12000)
    page.evaluate("notify('设置已保存')")
    for mode in ['network','malformed']:
        state['mode']=mode
        page.evaluate('refresh()')
        assert not page.evaluate('connected')
        assert page.locator('#connectionNotice').is_visible()
        state['mode']='ok';page.evaluate('refresh()')
        assert page.evaluate('connected')
        assert not page.locator('#connectionNotice').is_visible()
        assert page.locator('#notice').inner_text()=='设置已保存'
    assert not errors and not writes
    browser.close()
print(json.dumps({'passed':True,'automatic_recovery':True,'network_and_malformed_recovery':True,
                  'preserves_action_notices':True,'requests':state['requests'],'javascript_errors':errors,'production_writes':writes}))

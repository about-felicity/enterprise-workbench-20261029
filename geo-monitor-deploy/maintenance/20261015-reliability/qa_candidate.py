"""Real browser fault injection, isolated from production write endpoints."""
import json,sys,time
from pathlib import Path
import requests
from playwright.sync_api import sync_playwright
sys.path.insert(0,'/tmp/geo-reliability-stage')
from web_collectors.collector import BrowserCollector
from web_collectors.config import site_config

stage=Path('/tmp/geo-reliability-stage');report={'at':time.time()};errors=[]
capture=requests.get('http://127.0.0.1:8803/api/panel',timeout=30).json()
creation=requests.get('http://127.0.0.1:8804/api/panel',timeout=30).json()
catalog=requests.get('http://127.0.0.1:8804/api/catalog',timeout=60).json()
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    page=browser.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content('<main><div class="ds-markdown">短。</div><div class="ds-markdown">服务繁忙的含义。</div><button style="width:40px;height:40px" aria-label="停止生成"><svg></svg></button></main>')
    collector=BrowserCollector.__new__(BrowserCollector);collector.site=site_config('deepseek');collector.page=page
    snap=collector._snapshot()
    assert '短。' in snap['body'] and '服务繁忙的含义。' in snap['body'],snap
    assert snap['busy'] and not snap['providerError'],snap
    page.locator('button').evaluate("e=>e.setAttribute('aria-label','发送')")
    page.evaluate("()=>{let e=document.createElement('div');e.setAttribute('role','alert');e.textContent='服务繁忙';document.body.append(e)}")
    snap=collector._snapshot();assert not snap['busy'] and snap['providerError']
    report['short_fragments_icon_button_and_provider_alert_verified']=True
    for name,filename,panel in [('capture','panel.html',capture),('creation','creation-panel.html',creation)]:
        context=browser.new_context(viewport={'width':390,'height':900});page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)))
        mode={'offline':False,'posts':[],'drop':True}
        def route(r):
            path=r.request.url.split('geo.test',1)[1]
            if path.startswith('/api/control/'):
                mode['posts'].append({'id':r.request.headers['x-action-id'],'body':r.request.post_data,'path':path})
                if mode['drop']:mode['drop']=False;r.abort();return
                r.fulfill(json={'ok':True,'message':'操作已确认','result':{}});return
            if path=='/api/panel':
                if mode['offline']:r.abort();return
                r.fulfill(json=panel);return
            if path=='/api/catalog':r.fulfill(json=catalog);return
            r.fulfill(body=(stage/filename).read_text(),content_type='text/html')
        page.route('http://geo.test/**',route)
        page.goto('http://geo.test/')
        page.wait_for_function('connected===true')
        if name=='capture':page.evaluate("()=>perform('pause')")
        else:
            page.wait_for_function("document.querySelector('#question').options.length>0")
            page.locator('#new').click()
        page.locator('#retryAction').wait_for(state='visible')
        assert page.locator('#newBtn' if name=='capture' else '#new').is_disabled()
        page.reload();page.wait_for_function('connected===true');page.locator('#retryAction').click()
        page.wait_for_function('pendingAction===null && '+('working===false' if name=='capture' else 'busy===false'))
        assert len(mode['posts'])==2 and mode['posts'][0]==mode['posts'][1],mode['posts']
        mode['offline']=True
        page.evaluate('()=>refresh().catch(()=>{})');page.wait_for_function('connected===false')
        for selector in (['#pauseBtn','#resumeBtn','#saveBtn','#newBtn'] if name=='capture' else ['#new','#balance']):
            assert page.locator(selector).is_disabled(),selector
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
        report[name+'_lost_response_reload_same_action_and_offline_disable']=True
        context.close()
    browser.close()
assert not errors,errors
report['javascript_errors']=errors;report['production_writes']=0;report['extra_model_or_paid_requests']=0
(stage/'candidate-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

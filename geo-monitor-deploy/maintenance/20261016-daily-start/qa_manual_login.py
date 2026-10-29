"""Browser tests of the preview UI; all fixture POSTs are intercepted locally."""
import copy
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261016-manual-login')
base='http://127.0.0.1:3000'
port=int(sys.argv[1]) if len(sys.argv)>1 else 3001
report={'passed':False,'port':port,'scenarios':[],'page_errors':[]}

with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1500,'height':1000},permissions=['local-network-access'])
    def preview(route):
        route.fulfill(response=context.request.get(route.request.url.replace(':3000/',':'+str(port)+'/')))
    context.route(base+'/**',preview)
    actual=context.request.get(f'http://127.0.0.1:{port}/api/geo-capture/panel').json()
    # Bootstrap a real gateway session, then use fake model state for UI-only tests.
    context.request.get(base+'/api/geo-capture/panel')
    state={'mode':'login_required','polls':0,'posts':[]}
    def fixture_panel(route):
        data=copy.deepcopy(actual)
        model=next(m for m in data['models'] if m['id']=='deepseek')
        c=model['current'];c.update(state='paused',service_state='inactive',stop_requested=False,needs_review=0,pending_delivery=0)
        mode=state['mode'];ready=mode=='ready'
        model['manual_login']={'status':'closed'}
        model['login_status']={'status':'ready' if ready else 'checking' if mode=='checking' else 'login_required','message':'测试登录状态','checked_at':1}
        checks=[{'name':name,'ok':ready,'message':label} for name,label in
                [('settings','设置有效'),('login','登录有效'),('results','历史结果已核对'),('delivery','回传已核对'),('idle','进程已空闲')]]
        model['readiness']={'can_start':ready,'can_resume':ready,'checks':checks,'expires_at':4102444800 if ready else 1}
        route.fulfill(json=data)
    context.route(base+'/api/geo-capture/panel',fixture_panel)
    def fixture_post(route):
        action=route.request.url.rsplit('/',1)[1]
        assert action in {'login','login_open'},'Unexpected mutation in UI test: '+action
        state['posts'].append(action)
        if action=='login':state['mode']='checking'
        route.fulfill(json={'ok':True,'message':'测试操作已接受'})
    context.route(base+'/api/geo-capture/control/deepseek/*',fixture_post)
    def login_state(route):
        state['polls']+=1
        detected=state['polls']>=2
        if detected:state['mode']='ready'
        route.fulfill(json={'id':'fixture-flow','status':'verifying' if detected else 'opening','message':'正在校验登录'})
    context.route(base+'/api/geo-capture/login/state',login_state)
    page=context.new_page();page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
    page.goto(base+'/api/geo-capture/ui#deepseek',wait_until='domcontentloaded')
    page.locator('#modelTitle').filter(has_text='DeepSeek').wait_for()
    assert page.locator('#newBtn').is_disabled() and page.locator('#resumeBtn').is_disabled()
    assert page.get_by_role('button',name='登录 DeepSeek',exact=True).is_visible()
    page.get_by_role('button',name='重新校验',exact=True).click()
    assert page.locator('#loginBtn').is_disabled() and page.locator('#newBtn').is_disabled()
    report['scenarios'].append('登录失效和校验中均禁用开始及继续')
    state['mode']='ready';page.evaluate('refresh()')
    page.wait_for_function("document.getElementById('newBtn').disabled===false && document.getElementById('resumeBtn').disabled===false")
    assert page.locator('#newBtn').is_enabled() and page.locator('#resumeBtn').is_enabled()
    report['scenarios'].append('全部校验通过才启用开始及继续')
    page.locator('#questions').fill('未保存的问题')
    assert page.locator('#newBtn').is_disabled()
    page.locator('#resetBtn').click()
    state['mode']='login_required';page.evaluate('refresh()')
    with page.expect_popup() as info:page.locator('#manualLoginBtn').click()
    popup=info.value
    popup.wait_for_event('close',timeout=15000)
    page.wait_for_function("document.getElementById('newBtn').disabled===false")
    assert state['posts']==['login','login_open'],state['posts']
    report['scenarios'].append('检测登录后弹窗自动关闭，面板重新获取校验结果；未自动开始采集')
    page.screenshot(path=str(ROOT/'login-ready-fixture.png'))
    context.close()

    live=browser.new_context(viewport={'width':1500,'height':1000},permissions=['local-network-access'])
    def live_preview(route):route.fulfill(response=live.request.get(route.request.url.replace(':3000/',':'+str(port)+'/')))
    live.route(base+'/**',live_preview)
    page=live.new_page();page.on('pageerror',lambda error:report['page_errors'].append(str(error)))
    page.goto(base+'/api/geo-capture/ui#deepseek',wait_until='domcontentloaded')
    page.locator('#modelTitle').filter(has_text='DeepSeek').wait_for()
    assert page.locator('#newBtn').is_disabled() and page.locator('#resumeBtn').is_disabled()
    page.screenshot(path=str(ROOT/'login-running-live.png'))
    page.get_by_role('button',name='百度卡片',exact=False).click()
    page.wait_for_function("document.getElementById('modelTitle').textContent.includes('百度卡片')")
    assert page.locator('#captured').inner_text()=='15'
    assert page.locator('#processed').inner_text()=='15'
    assert '页面未公开引用' in page.locator('#progressDetail').inner_text()
    assert page.locator('#exceptions').inner_text().endswith('/ 0')
    report['baidu_capture']={'captured':15,'processed':15,'missing':0}
    report['scenarios'].append('真实运行任务按钮保持禁用；百度补采显示15/15，引用未公开单列')
    page.screenshot(path=str(ROOT/'baidu-complete-live.png'))
    for width in [1500,390]:
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    live.close();browser.close()

assert not report['page_errors'],report['page_errors']
report['passed']=True
(ROOT/('qa-production.json' if port==3000 else 'qa.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

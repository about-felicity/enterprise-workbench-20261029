"""Production UI reads and intercepted fixture writes. Never operates real tasks."""
import copy
from datetime import datetime,timedelta
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit,parse_qs
from playwright.sync_api import sync_playwright

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261016-daily-controls')
port=int(sys.argv[1]) if len(sys.argv)>1 else 3001
base='http://127.0.0.1:'+str(port)
report={'passed':False,'port':port,'scenarios':[],'page_errors':[]}
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1500,'height':1100},permissions=['local-network-access'])
    response=context.request.get(base+'/api/geo-capture/panel');assert response.ok
    live=response.json();today=live['today']
    assert all(m['daily']['progress_available'] for m in live['models'])
    state={'data':copy.deepcopy(live),'posts':[],'future_configs':{}}
    def recompute(model):
        d=model['daily'];cfg=d['config'];d['target']=len(cfg['questions'])*cfg['rounds']
        old={q['question']:q['completed'] for q in d['questions']}
        d['questions']=[{'question':q,'target':cfg['rounds'],'completed':old.get(q,0),
                          'remaining':max(0,cfg['rounds']-old.get(q,0))} for q in cfg['questions']]
        d['remaining']=sum(q['remaining'] for q in d['questions']);d['credited']=sum(min(q['completed'],q['target']) for q in d['questions'])
    def fixture_get(route):
        date=parse_qs(urlsplit(route.request.url).query).get('date',[today])[0]
        data=copy.deepcopy(state['data']);data['date']=date
        for model in data['models']:
            model['daily']['date']=date;model['daily']['editable']=date>=today
            if date!=today:
                model['daily']['status']='scheduled' if date>today else 'complete'
                if model['id']=='yuanbao':model['daily']['config']['rounds']=5 if date<today else 8
                if date>today and (date,model['id']) in state['future_configs']:
                    model['daily']['config']=state['future_configs'][(date,model['id'])]
                    recompute(model)
        route.fulfill(json=data)
    def fixture_post(route):
        action=route.request.url.rsplit('/',1)[-1];model_id=route.request.url.split('/')[-2]
        payload=route.request.post_data_json
        assert action in {'settings','pause','resume'},'Unexpected UI write '+action
        assert payload.get('day')>=today
        model=next(m for m in state['data']['models'] if m['id']==model_id)
        if payload['day']>today:
            assert action=='settings' and payload['apply_now'] is True
            state['future_configs'][(payload['day'],model_id)]={k:payload[k] for k in ('questions','rounds','interval')}
            state['posts'].append({'action':action,'model':model_id,'payload':payload})
            route.fulfill(json={'ok':True,'message':'未来计划已保存','revision':model['revision']});return
        d=model['daily']
        if action=='settings':
            assert payload['apply_now'] is True
            model['revision']+=1;cfg={k:payload[k] for k in ('questions','rounds','interval')}
            model['settings']=cfg;d['config']=cfg
            d['status']='paused' if d.get('desired')=='paused' else 'applying'
            recompute(model)
        else:
            assert payload['scope']=='daily'
            d['desired']='paused' if action=='pause' else 'running';d['status']='paused' if action=='pause' else 'queued'
        state['posts'].append({'action':action,'model':model_id,'payload':payload})
        route.fulfill(json={'ok':True,'message':'测试：已保存并应用','revision':model['revision']})
    context.route(base+'/api/geo-capture/panel*',fixture_get)
    context.route(base+'/api/geo-capture/control/**',fixture_post)
    page=context.new_page();page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
    page.goto(base+'/api/geo-capture/ui#yuanbao',wait_until='domcontentloaded')
    page.locator('#modelTitle').filter(has_text='元宝').wait_for()
    assert page.locator('.daily-model').count()==6
    assert page.locator('#dailyQuestions tr').count()==21
    assert page.locator('#rounds').input_value()=='8'
    assert page.locator('#dailyDescription').inner_text().find('105')>=0
    page.locator('#rounds').fill('9');assert page.locator('#saveBtn').is_enabled()
    page.locator('#saveBtn').click()
    page.wait_for_function("document.querySelector('#dailyDescription').textContent.includes('189')")
    assert state['posts'][-1]['payload']['rounds']==9
    report['scenarios'].append('保存按钮携带当天日期和立即应用指令；每天目标同步更新')
    page.locator('#pauseBtn').click()
    page.wait_for_function("document.querySelector('#dailyModels').textContent.includes('已暂停')")
    page.locator('#rounds').fill('10');page.locator('#saveBtn').click()
    page.wait_for_function("document.querySelector('#dailyDescription').textContent.includes('210')")
    assert next(m for m in state['data']['models'] if m['id']=='yuanbao')['daily']['desired']=='paused'
    page.locator('#resumeBtn').click()
    assert state['posts'][-1]['action']=='resume'
    report['scenarios'].append('手动暂停、暂停时保存保持暂停、手动继续均使用当天任务接口')
    yesterday=(datetime.strptime(today,'%Y-%m-%d')-timedelta(days=1)).date().isoformat()
    page.locator('#taskDate').fill(yesterday);page.locator('#taskDate').dispatch_event('change')
    page.wait_for_function("document.querySelector('#settingsTitle').textContent.includes('只读')")
    assert page.locator('#questions').is_disabled() and page.locator('#saveBtn').is_disabled()
    assert page.locator('#pauseBtn').is_disabled() and page.locator('#resumeBtn').is_disabled()
    assert page.locator('#rounds').input_value()=='5'
    report['scenarios'].append('历史日期完整配置可查看，历史任务不可误暂停或修改')
    tomorrow=(datetime.strptime(today,'%Y-%m-%d')+timedelta(days=1)).date().isoformat()
    page.locator('#taskDate').fill(tomorrow);page.locator('#taskDate').dispatch_event('change')
    page.wait_for_function("!document.querySelector('#questions').disabled")
    assert page.locator('#rounds').input_value()=='8'
    page.locator('#rounds').fill('9');page.locator('#saveBtn').click()
    page.wait_for_function("document.querySelector('#notice').textContent.includes('未来计划已保存')")
    assert state['posts'][-1]['payload']['day']==tomorrow
    report['scenarios'].append('未来日期可独立保存计划，不修改今天的任务配置')
    page.locator('#todayBtn').click();page.wait_for_function("!document.querySelector('#questions').disabled")
    assert page.locator('#rounds').input_value()=='10'
    # A failed refresh must retain date, draft, and displayed data.
    page.locator('#interval').fill('90')
    page.evaluate("notify('测试消息');")
    page.locator('#dailyModels .daily-model').filter(has_text='百度卡片').click()
    page.locator('#dailyModels .daily-model').filter(has_text='元宝').click()
    assert page.locator('#interval').input_value()=='90'
    report['scenarios'].append('模型切换保留未保存草稿')
    context.close()
    real=browser.new_context(viewport={'width':1500,'height':1100},permissions=['local-network-access'])
    real.route(base+'/api/geo-capture/control/**',lambda route:(_ for _ in ()).throw(AssertionError('Live QA must not mutate tasks')))
    page=real.new_page();page.on('pageerror',lambda e:report['page_errors'].append(str(e)))
    page.goto(base+'/api/geo-capture/ui#yuanbao',wait_until='domcontentloaded')
    page.locator('#dailyQuestions tr').first.wait_for(state='attached')
    assert page.locator('.daily-model').count()==6
    for width in [1600,1280,390]:
        page.set_viewport_size({'width':width,'height':1100})
        page.wait_for_timeout(200)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'),width
        if width==1600:page.screenshot(path=str(ROOT/'daily-controls-live.png'))
        if width==390:page.screenshot(path=str(ROOT/'daily-controls-mobile.png'))
    tomorrow=(datetime.strptime(today,'%Y-%m-%d')+timedelta(days=1)).date().isoformat()
    future=real.request.get(base+'/api/geo-capture/panel?date='+tomorrow).json()
    assert future['date']==tomorrow and all(m['daily']['editable'] for m in future['models'])
    assert all(m['daily']['status']=='scheduled' for m in future['models'])
    report['scenarios'].append('正式接口逐模型当天配置/进度和明日计划可读，1600/1280/390px无溢出')
    report['live_daily']={m['id']:{k:m['daily'][k] for k in ('target','completed','remaining','status')} for m in live['models']}
    browser.close()
assert not report['page_errors'],report['page_errors']
report['passed']=True
(ROOT/('qa-production.json' if port==3000 else 'qa-preview.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

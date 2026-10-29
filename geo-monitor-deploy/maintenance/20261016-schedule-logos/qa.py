"""Real production GET, isolated fixture schedule POST. Never mutates real timers."""
import copy,json,sys
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path('/opt/monitor/geo-capture/maintenance/20261016-schedule-logos');port=int(sys.argv[1]);base=f'http://127.0.0.1:{port}'
report={'passed':False,'port':port,'errors':[],'scenarios':[]}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1600,'height':1100})
 state={'posts':[],'schedule':None,'lost_reply':False,'fail_once':False}
 def fixture(route):
  assert route.request.method=='POST' and route.request.url.endswith('/control/schedule')
  data=route.request.post_data_json;state['posts'].append({'body':data,'key':route.request.headers['x-action-id']})
  if state['fail_once']:
   state['fail_once']=False;route.abort();return
  result={**state['schedule'],'enabled':data['enabled'],'time':data['time'],'revision':data['revision']+1,'next_run':'2026-10-17T06:35:00+08:00' if data['enabled'] else None}
  state['schedule']=result
  route.fulfill(json={'ok':True,'message':'fixture saved','schedule':result})
 context.route(base+'/api/geo-capture/control/**',fixture)
 def panel(route):
  response=context.request.get(route.request.url);data=response.json()
  if state['schedule'] is None:state['schedule']=data['schedule']
  data['schedule']=state['schedule'];route.fulfill(json=data)
 context.route(base+'/api/geo-capture/panel*',panel)
 page=context.new_page();page.on('pageerror',lambda error:report['errors'].append(str(error)))
 page.goto(base+'/api/geo-capture/ui#deepseek');page.locator('#dailyModels .daily-model').nth(5).wait_for(timeout=45000)
 assert page.locator('#scheduleTime').input_value()==state['schedule']['time']
 for image in page.locator('#dailyModels img.model-logo').all():
  assert image.evaluate('(e)=>e.complete&&e.naturalWidth>0')
 assert page.locator('#dailyModels img.model-logo').count()==6
 assert page.locator('#nav img.model-logo').count()==6
 report['scenarios'].append('六通道任务卡及切换栏使用真实模型Logo，本地内嵌加载')
 page.locator('#scheduleTime').fill('06:35');page.locator('#scheduleTime').dispatch_event('change')
 page.locator('#scheduleSave').click();page.wait_for_function("document.getElementById('scheduleSave').disabled")
 page.wait_for_timeout(250)
 assert state['posts'][-1]['body']['time']=='06:35'
 page.locator('#scheduleEnabled').uncheck();page.locator('#scheduleSave').click();page.wait_for_timeout(300)
 assert state['posts'][-1]['body']['enabled'] is False
 report['scenarios'].append('每天开始时间与定时开关可保存，独立全局接口，不操作模型任务')
 state['fail_once']=True;page.locator('#scheduleTime').fill('07:20');page.locator('#scheduleTime').dispatch_event('change');page.locator('#scheduleSave').click()
 page.get_by_role('button',name='核对并重试定时保存',exact=True).wait_for()
 first=state['posts'][-1];page.locator('#scheduleSave').click();page.wait_for_timeout(300)
 assert state['posts'][-1]==first
 report['scenarios'].append('丢失保存响应后使用原操作编号与原配置重试，避免重复变更')
 for width in (1600,1280,390):
  page.set_viewport_size({'width':width,'height':1100})
  assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
  page.screenshot(path=str(R/f'schedule-logos-{port}-{width}.png'),full_page=True)
 assert not report['errors'];report['passed']=True
 browser.close()
(R/('qa-preview.json' if port==3001 else 'qa-production.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))

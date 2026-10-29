import copy,json
from pathlib import Path
from playwright.sync_api import sync_playwright
R=Path('/opt/monitor/geo-capture/maintenance/20261016-deepseek-session');B='http://127.0.0.1:3000'
html=(R/'state-panel.html').read_text().replace("'/api/panel'","'/api/geo-capture/panel'")
errors=[];polls=[];stage={'ready':False}
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context();live=context.request.get(B+'/api/geo-capture/panel').json()
 def route(r):
  url=r.request.url
  assert r.request.method=='GET','No real or fixture POST expected'
  if '/login/state' in url:
   polls.append(url);stage['ready']=len(polls)>1
   r.fulfill(json={'status':'ready' if stage['ready'] else 'verifying'});return
  if '/panel' in url:
   data=copy.deepcopy(live);model=next(m for m in data['models'] if m['id']=='deepseek')
   state='running' if stage.get('running') else 'ready_to_resume' if stage['ready'] else 'checking_login'
   model['current'].update(state=state,service_state='active' if stage.get('running') else 'inactive')
   model['daily'].update(status=state,remaining=32)
   model['manual_login']={'status':'ready' if stage['ready'] else 'verifying'}
   model['login_status'].update(status='ready' if stage['ready'] else 'checking')
   model['readiness'].update(can_resume=stage['ready'],expires_at=4102444800)
   model['readiness']['checks']=[{'name':'login','ok':stage['ready'],'message':'fixture'}]
   if stage.get('running'):
    model['readiness'].update(can_resume=False,can_start=False,expires_at=1)
    model['readiness']['checks']=[{'name':'login','ok':False,'message':'任务运行中；启动前校验时效不影响本次采集'},{'name':'idle','ok':False,'message':'任务运行中，无需重复开始或继续'}]
   r.fulfill(json=data);return
  r.fulfill(body=html,content_type='text/html')
 context.route(B+'/**',route)
 page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto(B+'/api/geo-capture/ui#deepseek')
 page.locator('#taskState').filter(has_text='登录已恢复，待继续').wait_for(timeout=10000)
 assert page.locator('#dailyModels .selected').inner_text().startswith('登录已恢复，待继续')
 assert page.locator('#resumeBtn').is_enabled()
 assert len(polls)>=2 and all('/api/geo-capture/login/state' in u for u in polls)
 stage['running']=True;page.evaluate('refresh()')
 page.get_by_text('任务正在运行，采集器持续检查登录状态；无需重复登录或点击继续。',exact=True).wait_for(timeout=10000)
 assert page.locator('#manualLoginBtn').is_hidden()
 assert page.locator('#resumeBtn').is_disabled()
 assert page.locator('#readinessChecks li').evaluate_all("els=>els.every(e=>getComputedStyle(e).color==='rgb(115, 132, 124)')")
 assert not errors
 browser.close()
report={'passed':True,'automatic_ready_event_refresh':True,'correct_gateway_login_state_path':True,'task_and_daily_state_consistent':True,'resume_enabled_after_checks':True,'expired_preflight_is_neutral_while_running':True,'posts':0,'page_errors':errors}
(R/'qa-login-state.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

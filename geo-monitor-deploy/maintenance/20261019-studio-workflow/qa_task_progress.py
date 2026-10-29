import asyncio,copy,json,os,requests
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 base=requests.get('http://127.0.0.1:3000/api/geo-creation/panel',timeout=20).json();p=copy.deepcopy(base['studio']['plans'][0]);p.update(name='进度与暂停继续验收',frequency='daily',task_type='collect_write',enabled=True,questions=['问题一','问题二'],channels=['deepseek','baidu_ai','wenxin_card'],rounds=2,max_per_category=2)
 day=base['studio']['today'];t=dict(plan_id=p['plan_id'],date=day,status='collecting',target_per_model=4,questions=2,progress=[dict(id=k,completed=2,blocked={}) for k in p['channels']],writing_complete=1,articles=3,task_type='collect_write',name=p['name'],product={'id':'qa','name':p['product']['name']},writing_jobs=1,frequency='daily',capture_time='01:00',writing_time='04:00',error='')
 base['studio']['plans']=[p];base['studio']['daily_tasks']=[t];writes=[];errors=[]
 async with async_playwright() as pw:
  b=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox']);page=await b.new_page(viewport={'width':1366,'height':850});page.on('pageerror',lambda e:errors.append(str(e)))
  async def route(r):
   if r.request.method=='POST':
    assert r.request.url.endswith(('/control/day_pause','/control/day_resume'))
    v=r.request.post_data_json;assert v=={'plan_id':p['plan_id'],'date':day};writes.append(r.request.url.rsplit('/',1)[-1]);t['status']='paused' if writes[-1]=='day_pause' else 'collecting'
    return await r.fulfill(content_type='application/json',body=json.dumps({'ok':True,'result':{'message':'测试暂停继续'}}))
   if r.request.url.endswith('/api/geo-creation/panel'):return await r.fulfill(content_type='application/json',body=json.dumps(base))
   if r.request.url.endswith('/api/geo-creation/ui') and not os.environ.get('LIVE_UI'):return await r.fulfill(content_type='text/html',body=Path('/tmp/creation-panel-task-progress.html').read_text().replace("const API='/api/';","const API='/api/geo-creation/';"))
   await r.continue_()
  await page.route('**/*',route);await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected')
  bars=page.locator('#planQueue progress');assert await bars.count()==2
  assert await bars.nth(0).get_attribute('value')=='6' and await bars.nth(0).get_attribute('max')=='12'
  assert await bars.nth(1).get_attribute('value')=='1' and await bars.nth(1).get_attribute('max')=='2'
  await page.locator('#planQueue [data-day-action=day_pause]').click();await page.wait_for_function('!busy');assert await page.locator('#planQueue [data-day-action=day_resume]').count()==1
  assert await bars.nth(0).get_attribute('value')=='6'
  await page.locator('#planQueue [data-day-action=day_resume]').click();await page.wait_for_function('!busy');assert writes==['day_pause','day_resume']
  await page.screenshot(path='/tmp/creation-task-progress-desktop.png')
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1');await page.screenshot(path='/tmp/creation-task-progress-mobile.png',full_page=True)
  for state,enabled,kind in [('not_enabled',False,'collect_write'),('complete',True,'collect_write'),('capture_only',False,'capture_only')]:
   t['status']=state;t['task_type']=kind;p['enabled']=enabled;p['task_type']=kind;await page.evaluate('refresh()')
   if state=='capture_only':assert await page.locator('#planQueue progress').count()==1;assert await page.locator('#planQueue [data-day-action=day_pause]').count()==1
   else:assert await page.locator('#planQueue [data-control-unavailable]').is_disabled();assert await page.locator('#planQueue [data-day-action]').count()==0
  assert not errors,errors
  print(json.dumps({'capture_and_writing_progress_correct':True,'pause_resume_same_plan_and_date':True,'progress_preserved_after_pause':True,'draft_and_complete_disabled':True,'legacy_capture_only_pause_supported':True,'mobile_no_overflow':True,'page_errors':errors,'production_mutations':0}))
  await b.close()
asyncio.run(main())

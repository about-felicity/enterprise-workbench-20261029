import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
EMPTY=['kbName','kbBrand','kbAudience','kbFacts','planName','planQuestions','planProduct','planFrequency','planTaskType','planStart','planCapture','planWriting','planRounds','planCount','planArticleBudget','planTaskBudget']
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  page=await b.new_page();errors=[];writes=[];page.on('pageerror',lambda e:errors.append(str(e)))
  async def route(r):
   if r.request.method=='POST':
    assert '/control/plan_save' in r.request.url
    writes.append(r.request.post_data_json)
    return await r.fulfill(content_type='application/json',body=json.dumps({'ok':True,'result':{'plan_id':writes[-1].get('plan_id','qa'),'message':'测试保存成功'}}))
   if r.request.url.endswith('/api/geo-creation/ui') and not os.environ.get('LIVE_UI'):
    return await r.fulfill(content_type='text/html',body=Path('/tmp/creation-panel-allblank.html').read_text().replace("const API='/api/';","const API='/api/geo-creation/';"))
   await r.continue_()
  await page.route('**/*',route);await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected')
  async def empty():
   for f in EMPTY:assert await page.locator('#'+f).input_value()=='',f
   assert await page.locator('[name=planChannel]:checked').count()==0
  await empty();await page.evaluate('refresh()');await empty()
  for n in [2,3,1]:await page.locator(f'[data-wizard="{n}"]').click()
  await page.locator('#kbName').fill('输入保护');await page.evaluate('refresh()');assert await page.locator('#kbName').input_value()=='输入保护'
  await page.evaluate('newCreationTask()');await empty()
  assert await page.locator('#taskList').is_visible();assert await page.locator('#taskList [data-edit-plan]').count()>0
  plan=await page.evaluate('data.studio.plans[0]')
  await page.locator('#taskList [data-edit-plan]').first.click();assert await page.evaluate('wizardStep')==1
  assert await page.locator('#editorTitle').inner_text()=='编辑创作任务'
  assert await page.locator('#kbName').input_value()==plan['product']['name']
  await page.locator('[data-wizard="2"]').click();assert await page.locator('#planQuestions').input_value()=='\n'.join(plan['questions'])
  await page.locator('[data-wizard="3"]').click()
  for f,key in [('planFrequency','frequency'),('planTaskType','task_type'),('planCapture','capture_time'),('planWriting','writing_time'),('planStart','start_date')]:assert await page.locator('#'+f).input_value()==plan.get(key,{'frequency':'daily','task_type':'collect_write'}.get(key)),key
  await page.locator('#planName').fill('测试修改名称')
  await page.locator('#planCount').fill('2')
  await page.locator('#planSave').click();await page.wait_for_function('!busy')
  assert len(writes)==1,writes
  assert writes[0]['plan_id']==plan['plan_id'] and writes[0]['enabled']==plan['enabled']
  assert writes[0]['name']=='测试修改名称' and writes[0]['max_per_category']==2
  await empty()
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert not errors,errors
  print(json.dumps({'all_three_steps_blank':True,'refresh_preserves_input':True,'separate_task_list':True,'full_existing_config_loaded':True,'edit_saves_same_id_and_enable_state':True,'save_returns_blank':True,'mobile_no_overflow':True,'page_errors':errors,'writes':'one intercepted save; no production mutations'}))
  await b.close()
asyncio.run(main())

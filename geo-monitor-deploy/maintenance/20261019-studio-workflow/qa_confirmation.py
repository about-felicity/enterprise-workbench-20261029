import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  page=await b.new_page();errors=[];writes=[];fail_once=True;page.on('pageerror',lambda e:errors.append(str(e)))
  async def route(r):
   nonlocal fail_once
   if r.request.method=='POST':
    assert '/control/kb_save' in r.request.url
    writes.append(r.request.post_data_json)
    if fail_once:
     fail_once=False;return await r.fulfill(status=400,content_type='application/json',body=json.dumps({'ok':False,'message':'测试保存失败'}))
    return await r.fulfill(content_type='application/json',body=json.dumps({'ok':True,'result':{'product_id':writes[-1]['product_id'],'message':'测试确认成功'}}))
   if r.request.url.endswith('/api/geo-creation/ui') and not os.environ.get('LIVE_UI'):
    return await r.fulfill(content_type='text/html',body=Path('/tmp/creation-panel-confirm-gates.html').read_text().replace("const API='/api/';","const API='/api/geo-creation/';"))
   await r.continue_()
  await page.route('**/*',route);await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected');await page.evaluate('newCreationTask()')
  for n in [2,3]:
   await page.locator(f'[data-wizard="{n}"]').click();assert await page.evaluate('wizardStep')==1
  pid=await page.evaluate('data.studio.products[0].product_id');await page.locator('#kbSelect').select_option(pid)
  await page.locator('[data-wizard="2"]').click();assert await page.evaluate('wizardStep')==1
  await page.locator('#kbSave').click();await page.wait_for_function('!busy');assert await page.evaluate('wizardStep')==1
  await page.locator('#kbSave').click();await page.wait_for_function('!busy');assert await page.evaluate('wizardStep')==2
  await page.locator('[data-wizard="3"]').click();assert await page.evaluate('wizardStep')==2
  await page.locator('#planQuestions').fill('测试监测问题');await page.locator('[name=planChannel]').first.check()
  await page.locator('#toSchedule').click();assert await page.evaluate('wizardStep')==2
  await page.locator('#planRounds').fill('2');await page.locator('#toSchedule').click();assert await page.evaluate('wizardStep')==3
  await page.locator('[data-wizard="2"]').click();await page.locator('#planQuestions').fill('修改后的测试问题')
  await page.locator('[data-wizard="3"]').click();assert await page.evaluate('wizardStep')==2
  await page.locator('#toSchedule').click();assert await page.evaluate('wizardStep')==3
  await page.locator('[data-wizard="1"]').click();await page.locator('#kbBrand').fill('修改品牌')
  await page.locator('[data-wizard="3"]').click();assert await page.evaluate('wizardStep')==1
  await page.locator('#kbSave').click();await page.wait_for_function('!busy');assert await page.evaluate('wizardStep')==2
  await page.locator('[data-wizard="3"]').click();assert await page.evaluate('wizardStep')==2
  await page.locator('#toSchedule').click();assert await page.evaluate('wizardStep')==3
  await page.evaluate('refresh()');assert await page.evaluate('knowledgeReady()')
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  await page.evaluate('newCreationTask()');await page.locator('[data-wizard="2"]').click();assert await page.evaluate('wizardStep')==1
  assert not errors,errors
  print(json.dumps({'blank_cannot_skip':True,'selecting_existing_requires_confirmation':True,'failed_save_stays_step1':True,'successful_confirmation_advances':True,'questions_require_confirmation_and_rounds':True,'changes_invalidate_confirmation':True,'refresh_preserves_confirmation':True,'new_form_resets_confirmation':True,'mobile_no_overflow':True,'page_errors':errors,'production_mutations':0}))
  await b.close()
asyncio.run(main())

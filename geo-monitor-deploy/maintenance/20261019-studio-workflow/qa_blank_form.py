import asyncio,json,os
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  page=await b.new_page();errors=[];posts=[];page.on('pageerror',lambda e:errors.append(str(e)))
  async def route(r):
   if r.request.method=='POST':posts.append(r.request.url);return await r.abort()
   if r.request.url.endswith('/api/geo-creation/ui') and not os.environ.get('LIVE_UI'):
    return await r.fulfill(content_type='text/html',body=Path('/tmp/creation-panel-blank-fix.html').read_text().replace("const API='/api/';","const API='/api/geo-creation/';"))
   await r.continue_()
  await page.route('**/*',route);await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected')
  fields=['kbName','kbBrand','kbAudience','kbFacts','planName','planQuestions','planProduct','planSelect','kbSelect']
  for f in fields:assert await page.locator('#'+f).input_value()=='',f
  assert await page.locator('#kbExtracted').is_hidden()
  # A polling refresh must not load the server pending import or first existing product.
  await page.evaluate('refresh()')
  for f in fields:assert await page.locator('#'+f).input_value()=='',f
  await page.locator('#kbName').fill('用户正在输入的产品');await page.locator('#kbFacts').fill('用户填写的资料')
  await page.evaluate('refresh()');assert await page.locator('#kbName').input_value()=='用户正在输入的产品'
  # Only an explicit product choice fills the form.
  pid=await page.evaluate('data.studio.products[0].product_id')
  await page.locator('#kbSelect').select_option(pid);assert await page.locator('#kbName').input_value()
  assert await page.locator('#planProduct').input_value()==pid
  await page.locator('#kbNew').click()
  for f in fields:assert await page.locator('#'+f).input_value()=='',f
  plans=await page.evaluate('data.studio.plans.length')
  if plans:
   await page.locator('[data-edit-plan]').first.click();assert await page.evaluate('wizardStep')==2
   assert await page.locator('#planQuestions').input_value();assert await page.evaluate('!!planId')
   assert await page.locator('#kbName').input_value()
   await page.locator('[data-wizard="3"]').click();await page.locator('#planNew').click()
   for f in fields:assert await page.locator('#'+f).input_value()=='',f
  # Explicit upload results still populate and survive polling until confirmation.
  await page.evaluate("studioResult('kb_import',{import_id:'qa-only',filename:'qa.docx',paragraphs:1,text:'测试事实',analysis:{name:'测试导入产品',brand:'测试品牌',facts:['测试事实']}})")
  await page.evaluate('refresh()');assert await page.locator('#kbName').input_value()=='测试导入产品'
  await page.evaluate("studioResult('plan_save',{plan_id:'qa-only'})")
  for f in fields:assert await page.locator('#'+f).input_value()=='',f
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert not posts,posts;assert not errors,errors
  print(json.dumps({'initial_fields_empty':True,'polling_preserves_input':True,'explicit_product_select_works':True,'existing_task_edit_works':bool(plans),'new_task_clears_editor':True,'upload_populates_only_on_action':True,'after_save_returns_to_blank':True,'mobile_no_overflow':True,'post_requests':posts,'page_errors':errors}))
  await b.close()
asyncio.run(main())

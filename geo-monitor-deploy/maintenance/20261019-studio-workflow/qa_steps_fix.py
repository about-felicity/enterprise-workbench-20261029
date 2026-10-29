import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  page=await b.new_page();errors=[];posts=[];page.on('pageerror',lambda e:errors.append(str(e)))
  async def route(r):
   if r.request.method=='POST':posts.append(r.request.url);return await r.abort()
   if r.request.url.endswith('/api/geo-creation/ui'):
    h=Path('/tmp/creation-panel-step-fix.html').read_text().replace("const API='/api/';","const API='/api/geo-creation/';")
    return await r.fulfill(content_type='text/html',body=h)
   await r.continue_()
  await page.route('**/*',route)
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected')
  assert await page.evaluate('kbDirty')
  for n,section in [(2,'dailyPlan'),(3,'schedule'),(1,'knowledge')]:
   await page.locator(f'[data-wizard="{n}"]').click();assert await page.locator('#'+section).is_visible()
   assert await page.locator('#wizardFeedback').is_visible()
  await page.locator('[data-wizard="3"]').click();await page.locator('#planEnable').click()
  assert await page.evaluate('wizardStep')==1
  assert '尚未确认' in await page.locator('#wizardFeedback').inner_text()
  await page.evaluate('connected=false;buttons()')
  assert not await page.locator('[data-wizard="2"]').is_disabled()
  await page.locator('[data-wizard="2"]').click();assert await page.locator('#dailyPlan').is_visible()
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
  assert not posts,posts;assert not errors,errors
  print(json.dumps({'steps_1_2_3_clickable':True,'unsaved_product_prevents_task_save':True,'inline_reason_visible':True,'offline_browsing':True,'mobile_no_overflow':True,'post_requests':posts,'page_errors':errors}))
  await b.close()
asyncio.run(main())

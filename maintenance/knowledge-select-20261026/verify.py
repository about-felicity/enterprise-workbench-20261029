import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  page=await browser.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  async def guard(route):
   if route.request.method!='GET':raise AssertionError('Unexpected mutation')
   await route.fulfill(response=await route.fetch())
  await page.route('**/api/geo-creation/**',guard)
  async def check(label,candidate=None):
   if candidate:
    async def html(route):
     body=Path(candidate).read_text().replace("const API='/api/';","const API='/api/geo-creation/';")
     await route.fulfill(content_type='text/html',body=body)
    await page.route('**/api/geo-creation/ui',html)
   await page.goto('http://192.168.31.106:3000/api/geo-creation/ui')
   await page.wait_for_function("data?.studio?.products?.length===9 && document.querySelector('#kbSelect').options.length===10")
   await page.evaluate("newCreationTask();$('kbSearch').value='__no_match__';filterKnowledgeOptions()")
   assert await page.locator('#kbSelect option:not([hidden])').count()==1
   await page.evaluate('newCreationTask()')
   visible=await page.locator('#kbSelect option:not([hidden])').count()
   if label=='before':
    assert visible==1,visible
    print('Reproduced: cleared search still hides all products');return
   assert visible==10,visible
   ids=await page.evaluate('data.studio.products.map(p=>p.product_id)')
   for pid in ids:
    await page.locator('#kbSelect').select_option(pid)
    await page.locator('#kbSave').click()
    assert await page.locator('#dailyPlan').is_visible()
    assert await page.locator('#planProduct').input_value()==pid
    await page.evaluate('newCreationTask()')
   pending=await page.evaluate('data.studio.knowledge_library.find(r=>!r.product_id).name')
   await page.locator('#kbSearch').fill(pending)
   assert '待分析' in await page.locator('#kbSearchHint').inner_text()
   await page.locator('#kbSearchHint button').click()
   assert await page.locator('#kbSelect option:not([hidden])').count()==10
   assert not errors,errors
   print(json.dumps({'success':True,'selected_products':len(ids),'search_reset':True,'pending_hint':True,'page_errors':errors}))
  import sys
  if len(sys.argv)>1 and sys.argv[1]=='--live':await check('live')
  elif len(sys.argv)>1:await check('candidate',sys.argv[1])
  else:await check('before')
  await browser.close()

asyncio.run(main())

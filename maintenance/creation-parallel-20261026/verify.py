import asyncio,json,sys
from pathlib import Path
from playwright.async_api import async_playwright

async def main():
 async with async_playwright() as pw:
  b=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  p=await b.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  async def guard(route):
   assert route.request.method=='GET'
   await route.fulfill(response=await route.fetch())
  await p.route('**/api/geo-creation/**',guard)
  if len(sys.argv)>1:
   async def html(route):
    await route.fulfill(content_type='text/html',body=Path(sys.argv[1]).read_text().replace("const API='/api/';","const API='/api/geo-creation/';"))
   await p.route('**/api/geo-creation/ui',html)
  await p.goto('http://192.168.31.106:3000/api/geo-creation/ui')
  await p.wait_for_function("data?.studio?.products?.length===9 && document.querySelector('#kbSelect').options.length===10")
  await p.evaluate('newCreationTask()')
  assert await p.locator('#kbSearch,#kbSearchHint,#planWriting').count()==0
  ids=await p.evaluate('data.studio.products.map(p=>p.product_id)')
  for pid in ids:
   assert await p.locator('#kbSelect option:not([hidden])').count()==10
   await p.locator('#kbSelect').select_option(pid)
   await p.locator('#kbSave').click()
   assert await p.locator('#dailyPlan').is_visible()
   assert await p.locator('#planProduct').input_value()==pid
   payload=await p.evaluate('planPayload()')
   assert payload['analysis_start']=='after_capture' and 'writing_time' not in payload
   await p.evaluate('newCreationTask()')
  await p.evaluate('refresh()')
  assert await p.locator('#kbSelect option:not([hidden])').count()==10
  assert not errors,errors
  print(json.dumps({'success':True,'selectable_products':len(ids),'search_removed':True,'page_errors':errors}))
  await b.close()

asyncio.run(main())

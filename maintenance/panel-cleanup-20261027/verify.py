import asyncio,json
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as pw:
  browser=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1550,'height':1050},device_scale_factor=1)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/',wait_until='networkidle')
  assert await page.locator('.workbench-logo path').count()==4
  assert await page.get_by_text('企业概率监控',exact=True).count()==0
  assert await page.get_by_text('DAILY PERFORMANCE',exact=True).count()==0
  assert await page.locator('.topbar h1').is_visible()
  await page.screenshot(path='/tmp/panel-clean-overview.png',full_page=False)
  views=['问题对比','信源洞察','品牌与产品','回答审计','采集控制','内容创作中心']
  for label in views:
   await page.locator('.sidebar nav button').filter(has_text=label).click()
   await page.wait_for_timeout(400)
   assert await page.locator('.topbar h1').is_visible()
  for route in ['api/geo-capture/panel','api/geo-creation/panel','api/geo-creation/ui','asset-management/']:
   response=await page.request.get('http://127.0.0.1:3000/'+route)
   assert response.ok,(route,response.status)
  assert not errors,errors
  await page.set_viewport_size({'width':390,'height':844})
  await page.locator('.sidebar nav button').filter(has_text='模型总览').click()
  await page.screenshot(path='/tmp/panel-clean-mobile.png',full_page=False)
  print(json.dumps({'views_checked':7,'api_routes':4,'page_errors':errors,'svg_paths':4}))
  await browser.close()
asyncio.run(main())

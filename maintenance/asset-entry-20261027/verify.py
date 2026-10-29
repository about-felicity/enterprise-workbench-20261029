import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
D=Path('/tmp/asset-entry-verification');D.mkdir(exist_ok=True)
async def main():
 async with async_playwright() as pw:
  b=await pw.chromium.launch(headless=True,executable_path='/usr/bin/google-chrome',args=['--no-sandbox'])
  p=await b.new_page(viewport={'width':1530,'height':1050});errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  await p.goto('http://127.0.0.1:3000/',wait_until='networkidle')
  link=p.get_by_role('link',name='资产管理',exact=True)
  assert await link.count()==1 and await link.is_visible()
  assert await p.locator('.brand a').count()==0
  box=await link.bounding_box();assert box['width']>200 and box['height']>=44
  await p.screenshot(path=str(D/'desktop.png'))
  await link.hover();await p.screenshot(path=str(D/'hover.png'))
  await p.set_viewport_size({'width':390,'height':844})
  await link.scroll_into_view_if_needed();assert await link.is_visible()
  box=await link.bounding_box();assert box['x']>=0 and box['x']+box['width']<=390
  await p.screenshot(path=str(D/'mobile.png'))
  await link.click();await p.wait_for_url('**/asset-management**')
  assert (await p.request.get(p.url)).ok
  assert not errors,errors
  result={'desktop_and_mobile':True,'link':p.url,'page_errors':errors}
  (D/'report.json').write_text(json.dumps(result));print(json.dumps(result))
  await b.close()
asyncio.run(main())

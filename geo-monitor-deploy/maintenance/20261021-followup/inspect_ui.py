import asyncio,json
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await b.new_page();errors=[];failures=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('response',lambda r:failures.append({'url':r.url.split('?')[0],'status':r.status}) if r.status>=400 else None)
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui')
  await page.wait_for_timeout(2000)
  value={'url':page.url,'title':await page.title(),'errors':errors,'failed_responses':failures,'text':(await page.locator('body').inner_text())[:1000]}
  print(json.dumps(value,ensure_ascii=False));await b.close()
asyncio.run(main())

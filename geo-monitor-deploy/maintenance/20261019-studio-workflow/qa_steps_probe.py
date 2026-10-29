import asyncio,json
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await b.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_timeout(2500)
  print(json.dumps(await page.evaluate("({connected,busy,kbDirty,pending:!!pendingAction,kbName:$('kbName').value,product:!!$('planProduct').value,disabled:document.querySelector('[data-wizard=\"2\"]').disabled,message:$('message').textContent})"),ensure_ascii=False))
  await page.locator('[data-wizard="2"]').click(timeout=3000)
  print(json.dumps(await page.evaluate("({wizardStep,message:$('message').textContent,messageY:$('message').getBoundingClientRect().y,navY:$('wizardNav').getBoundingClientRect().y})"),ensure_ascii=False));print('errors',errors)
  await b.close()
asyncio.run(main())

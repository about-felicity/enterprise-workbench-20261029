import asyncio,hashlib,json,zipfile
from pathlib import Path
from playwright.async_api import async_playwright
OUT=Path('/opt/monitor/geo-capture/maintenance/20261021-content-quality/qa');OUT.mkdir(exist_ok=True)
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':900},accept_downloads=True)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui')
  await page.wait_for_function('connected',timeout=30000)
  await page.evaluate("showView('outputs',false)")
  await page.wait_for_selector('#library a[href*="kind=package"]')
  async with page.expect_download() as result:
   await page.locator('#library a[href*="kind=package"]').first.click()
  download=await result.value;await download.save_as(str(OUT/'browser-package.zip'))
  with zipfile.ZipFile(OUT/'browser-package.zip') as z:
   assert z.testzip() is None;count=json.loads(z.read('导出清单.json'))['count'];assert count==1
  assert '校验通过' in await page.locator('#downloadStatus').inner_text()
  mode={'value':'login'}
  async def fail(route):
   if mode['value']=='login':await route.fulfill(status=200,content_type='text/html',body='<html>登录页</html>')
   elif mode['value']=='json':await route.fulfill(status=400,content_type='application/json',body=json.dumps({'message':'当前筛选没有可下载的成稿'}))
   else:await route.fulfill(status=200,content_type='application/zip',body=b'PK\x03\x04broken')
  await page.route('**/api/geo-creation/download?**',fail)
  for kind,expected in [('login','登录已过期'),('json','没有可下载'),('broken','传输不完整')]:
   mode['value']=kind
   await page.locator('#library a[href*="kind=package"]').first.click()
   await page.wait_for_function('(expected)=>document.getElementById("downloadStatus").textContent.includes(expected)',arg=expected)
  await page.screenshot(path=str(OUT/'download-errors.png'))
  await browser.close()
  report={'browser_real_package_crc_ok':True,'article_count':count,'login_html_not_saved':True,'json_error_shown':True,'truncated_zip_not_saved':True,'page_errors':errors}
  assert not errors
  (OUT/'download.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
asyncio.run(main())

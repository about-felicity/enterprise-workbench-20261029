"""Browser downloads after all-article checks, using current certificates."""
import asyncio,json,sys,zipfile,hashlib
from urllib.parse import urlsplit,parse_qs
from pathlib import Path
from playwright.async_api import async_playwright
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
M=Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic')
OUT=M/'browser-qa';OUT.mkdir(exist_ok=True)
report=runtime.read(M/'all-final-report.json');current=[r for r in report['articles'] if r.get('folder')]
ready=[r for r in current if r.get('download_status')=='ready'];held=[r for r in current if r.get('download_status')=='needs_revision']
assert len(ready)==4 and len(held)==169
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':900},accept_downloads=True);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected',timeout=30000)
  await page.evaluate("()=>{showView('outputs',false);for(const id of ['dateFilter','productFilter','search'])$(id).value='';$('outputFilter').value='all';applyFilters()}")
  assert await page.locator('#library .output').count()==4
  target=page.locator('#library a[href*="kind=word"]').first
  query=parse_qs(urlsplit(await target.get_attribute('href')).query)
  item=next(r for r in ready if r['id']==query['article'][0] and ('legacy-original' if r['root']==str(runtime.SHARED) else Path(r['root']).name)==query['job'][0])
  async with page.expect_download() as event:await target.click()
  dl=await event.value;await dl.save_as(str(OUT/'current-ready.docx'))
  assert hashlib.sha256((OUT/'current-ready.docx').read_bytes()).hexdigest()==item['word_sha256']
  async with page.expect_download() as event:await page.locator('#downloadAll').click()
  dl=await event.value;await dl.save_as(str(OUT/'current-passed-4.zip'))
  with zipfile.ZipFile(OUT/'current-passed-4.zip') as z:
   assert z.testzip() is None;manifest=json.loads(z.read('导出清单.json'));assert manifest['count']==4
  rejected=held[0];job='legacy-original' if rejected['root']==str(runtime.SHARED) else Path(rejected['root']).name
  result=await page.evaluate('async ([job,id])=>{const r=await fetch(link(job,id,"word"));return {status:r.status,body:await r.json()}}',[job,rejected['id']]);assert result['status']==400
  empty=await page.evaluate('async ()=>{const r=await fetch(link("all-approved","","bundle")+"&date=2099-01-01");return {status:r.status,body:await r.json()}}');assert empty['status']==400
  await page.screenshot(path=str(OUT/'current-downloads.png'),full_page=True)
  await browser.close();assert not errors
  result={'browser_word_matches_receipt':True,'zip_crc_ok':True,'zip_articles':manifest['count'],
   'held_word_http':400,'empty_filter_http':400,'page_errors':errors,'held_current_articles':len(held)}
  (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result))
asyncio.run(main())

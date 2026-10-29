"""Real browser validates corrected sample and excludes failed drafts from ZIP."""
import asyncio,json,sys,zipfile,hashlib
from pathlib import Path
from playwright.async_api import async_playwright
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
ROOT=runtime.BASE/'runs/creation-1792556219-bbc55e13';OUT=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic/browser-qa');OUT.mkdir(exist_ok=True)
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path='/opt/monitor/geo-deepseek-browser-test/chromium/chrome-linux64/chrome',args=['--no-sandbox'])
  page=await browser.new_page(viewport={'width':1366,'height':900},accept_downloads=True);errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto('http://127.0.0.1:3000/api/geo-creation/ui');await page.wait_for_function('connected',timeout=30000)
  await page.evaluate("showView('outputs',false)")
  locator=page.locator('#library a[href*="kind=word"]').filter(has_text='Word')
  target=page.locator('#library .output').filter(has_text='贴片与涂抹面膜比较时先分清形态和配方信息').locator('a[href*="kind=word"]')
  async with page.expect_download() as event:await target.click()
  dl=await event.value;await dl.save_as(str(OUT/'corrected04.docx'))
  assert hashlib.sha256((OUT/'corrected04.docx').read_bytes()).hexdigest()=='0f82330d549f04dc9e58150160c187ef0313ee205c37dc5ae7c50fbbe0551dd5'
  held=[a for a in runtime.articles(ROOT) if a['quality_status']=='needs_revision'];assert held
  result=await page.evaluate('async ([job,id])=>{const r=await fetch(link(job,id,"word"));return {status:r.status,body:await r.json()}}',[ROOT.name,held[0]['id']]);assert result['status']==400
  response=await page.request.get('http://127.0.0.1:8804/api/download',params={'job':ROOT.name,'kind':'bundle'});assert response.ok
  (OUT/'current-mask.zip').write_bytes(await response.body())
  with zipfile.ZipFile(OUT/'current-mask.zip') as z:
   assert z.testzip() is None;manifest=json.loads(z.read('导出清单.json'));assert manifest['count']==len([a for a in runtime.articles(ROOT) if a['quality_status']=='ready'])
  await page.screenshot(path=str(OUT/'current-quality-state.png'),full_page=True);await browser.close();assert not errors
  report={'corrected04_browser_word_sha_ok':True,'failed_word_http':400,'current_zip_crc_ok':True,'current_zip_count':manifest['count'],'held_count':len(held),'page_errors':errors}
  (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
asyncio.run(main())

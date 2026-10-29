import asyncio,json,sys,io,zipfile
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
   async def html(route):await route.fulfill(content_type='text/html',body=Path(sys.argv[1]).read_text().replace("const API='/api/';","const API='/api/geo-creation/';"))
   await p.route('**/api/geo-creation/ui',html)
  await p.goto('http://192.168.31.106:3000/api/geo-creation/ui')
  await p.wait_for_function("Number(document.querySelector('#totalArticles').textContent)>0")
  await p.evaluate("showView('outputs',false)")
  assert await p.locator('#library .output').count()>0
  await p.locator('#outputFilter').select_option('new')
  await p.locator('#dateFilter').select_option('2026-10-26')
  count=await p.locator('#library .output').count();assert count==3,count
  href=await p.locator('#library .output a').filter(has_text='Word').first.get_attribute('href')
  response=await p.request.get('http://192.168.31.106:3000'+href)
  assert response.ok
  with zipfile.ZipFile(io.BytesIO(await response.body())) as z:assert 'word/document.xml' in z.namelist()
  await p.locator('#library .article-view[data-kind="markdown"]').first.click()
  await p.wait_for_function("document.querySelector('#previewText').textContent.length>100")
  await p.evaluate("$('preview').close();showView('knowledge',false)")
  assert await p.locator('#knowledgeRows .card').count()>0
  await p.locator('#librarySearch').fill('不存在的产品xyz')
  assert await p.locator('#knowledgeRows .card').count()==0
  await p.locator('#librarySearch').fill('')
  await p.evaluate("showView('outputs',false)")
  assert await p.locator('#library .output').count()==3
  assert not errors,errors
  print(json.dumps({'articles':count,'word_download':True,'preview':True,'knowledge_filter_independent':True,'page_errors':errors}))
  await b.close()
asyncio.run(main())

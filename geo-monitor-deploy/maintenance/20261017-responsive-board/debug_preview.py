import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 c=b.new_context(viewport={'width':1366,'height':768});page=c.new_page()
 page.on('console',lambda e:print('CONSOLE',e.type,e.text[:500]) if e.type=='error' else None)
 page.on('requestfailed',lambda r:print('FAILED',r.url[:180],r.failure))
 page.on('pageerror',lambda e:print('JS',str(e)))
 def guard(route):
  if route.request.method!='GET':route.abort()
  elif route.request.url.startswith('http://127.0.0.1:3000/'):
   route.fulfill(response=c.request.get(route.request.url.replace(':3000/',':3001/')))
  else:route.continue_()
 page.route('**/*',guard)
 page.goto('http://127.0.0.1:3000/',wait_until='domcontentloaded')
 page.wait_for_timeout(10000)
 print(json.dumps({'url':page.url,'text':page.locator('body').inner_text()[:3500]},ensure_ascii=False))
 b.close()

import json,time
from pathlib import Path
from playwright.sync_api import sync_playwright
BASE='http://127.0.0.1:3000';ROOT=Path('/opt/monitor/geo-capture/maintenance/20261016-deepseek-session')
html=(ROOT/'fast-login.html').read_text().replace("'/api/login/'","'/api/geo-capture/login/'")
posts=[];paths=[];errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context()
 def route(request):
  url=request.request.url;paths.append(url)
  if url.endswith('/login/ui'):request.fulfill(body=html,content_type='text/html');return
  if url.endswith('/login/state'):request.fulfill(json={'status':'waiting_login','id':'fixture-flow','csrf':'a'*64,'message':'fixture'});return
  if url.endswith('/login/frame'):request.fulfill(status=503,body='fixture');return
  if url.endswith('/login/input'):posts.append(request.request.post_data_json);request.fulfill(json={'ok':True});return
  raise AssertionError('Unexpected request '+url)
 context.route(BASE+'/**',route)
 page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
 page.goto(BASE+'/api/geo-capture/login/ui');page.wait_for_function("csrf.length===64&&waiting")
 canvas=page.locator('#screen');canvas.click();canvas.press_sequentially('12345678901',delay=0);canvas.press('Backspace')
 page.wait_for_function("textBuffer===''",timeout=3000);page.wait_for_timeout(400)
 assert [x['type'] for x in posts]==['click','text','key'],posts
 assert posts[1]['text']=='12345678901' and posts[2]['key']=='Backspace'
 assert all(x['flow']=='fixture-flow' for x in posts)
 assert not any('/panel' in path for path in paths)
 assert len([url for url in paths if url.endswith('/frame')])>=2
 assert not errors
 browser.close()
report={'passed':True,'heavy_panel_bootstrap_removed':True,'fast_text_batch_preserves_order':True,'input_not_replayed':True,'frame_polling_independent':True,'page_errors':errors,'fixture_posts':len(posts)}
(ROOT/'qa-login-speed.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

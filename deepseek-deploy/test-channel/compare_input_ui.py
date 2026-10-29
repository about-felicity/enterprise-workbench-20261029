import json,sys,time
from pathlib import Path
from playwright.sync_api import sync_playwright
sys.path.insert(0,'/tmp');from vps_geo_access import browser_cookie
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-input-latency');url='https://1any.top/geo_monitor/api/geo-capture/login/deepseek_test/ui'
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 c=b.new_context(viewport={'width':390,'height':844},permissions=['local-network-access'])
 c.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
 page=c.new_page();page.goto(url,wait_until='domcontentloaded',timeout=60000)
 results={}
 for mode,expected in [('original',2),('optimized',1)]:
  if mode=='original':page.route(url,lambda route:route.fulfill(status=200,content_type='text/html',body=(ROOT/'backup/deepseek_login.html').read_text()))
  else:page.unroute(url)
  page.goto(url,wait_until='domcontentloaded',timeout=60000)
  page.wait_for_function("document.getElementById('screen').naturalWidth>0&&waiting",timeout=30000,polling=100)
  responses=[]
  def got(r):
   if r.request.method=='POST' and r.url.split('?')[0].endswith('/deepseek_test/input'):responses.append({'at':time.monotonic(),'ok':r.ok})
  page.on('response',got);samples=[]
  for x,y in [(48,100),(680,600)]:
   rect=page.locator('#screen').bounding_box();responses.clear();start=time.monotonic()
   page.mouse.click(rect['x']+x/720*rect['width'],rect['y']+y/1280*rect['height'])
   deadline=time.monotonic()+25
   while len(responses)<expected and time.monotonic()<deadline:page.wait_for_timeout(50)
   assert len(responses)==expected and all(r['ok'] for r in responses),(mode,responses)
   samples.append({'input_requests':len(responses),'all_input_ack_ms':round((responses[-1]['at']-start)*1000,1)})
   page.wait_for_timeout(300)
  page.remove_listener('response',got);results[mode]=samples
 b.close()
(ROOT/'ui-public-comparison.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))

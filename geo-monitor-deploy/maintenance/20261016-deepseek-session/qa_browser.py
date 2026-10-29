"""Real Chrome, offline provider fixture, independent of the production account."""
import json,os,tempfile
from pathlib import Path
from playwright.sync_api import sync_playwright
from web_collectors import session_store as store

class Page:
 def __init__(self,page,context):
  self.page=page;self.cdp=context.new_cdp_session(page);self.cdp.send('Page.enable')
 def evaluate(self,script):return self.page.evaluate(script)
 def call(self,method,params=None):return self.cdp.send(method,params or {})

with tempfile.TemporaryDirectory() as temp,sync_playwright() as p:
 os.environ['GEO_DEEPSEEK_PROFILE_DIR']=temp+'/private-profile'
 profile=temp+'/chrome'
 def launch():
  c=p.chromium.launch_persistent_context(profile,executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
  c.route('https://chat.deepseek.com/**',lambda route:route.fulfill(body='<html><body><textarea></textarea></body></html>',content_type='text/html'))
  return c
 first=launch();page=first.pages[0];page.goto(store.ORIGIN)
 page.evaluate("localStorage.setItem('userToken','fixture-only-token');sessionStorage.setItem('fixture-session','fixture-only-state')")
 first.add_cookies([{'name':'ds_session_id','value':'fixture-only-cookie','domain':'chat.deepseek.com','path':'/','secure':True}])
 assert store.checkpoint(Page(page,first));first.close()
 second=launch();second.clear_cookies();page=second.pages[0]
 adapter=Page(page,second);assert store.restore(adapter);page.goto(store.ORIGIN)
 assert page.evaluate("localStorage.getItem('userToken')==='fixture-only-token' && sessionStorage.getItem('fixture-session')==='fixture-only-state'")
 assert any(c['name']=='ds_session_id' and c['value']=='fixture-only-cookie' for c in second.cookies())
 assert store.state_path().stat().st_mode&0o777==0o600
 store.invalidate();assert not store.restore(adapter)
 second.close()
report={'passed':True,'real_chrome_restart':True,'lost_session_cookie_restored':True,'session_storage_restored':True,'local_storage_preserved':True,'private_state_file':True,'invalidated_session_blocked':True,'production_account_used':False}
Path('/opt/monitor/geo-capture/maintenance/20261016-deepseek-session/qa-browser.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))

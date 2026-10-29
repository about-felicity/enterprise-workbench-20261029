"""Read-only production/public checks. Never opens login or submits test questions."""
import hashlib,json,sqlite3,sys,time
from pathlib import Path
sys.path.insert(0,'/tmp')
sys.path.insert(0,'/opt/monitor/geo-capture')
sys.path.insert(0,'/home/user/redroid-deepseek/code')
from vps_geo_access import browser_cookie
from playwright.sync_api import sync_playwright
from control_panel import Controller
from reader import Reader

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-deepseek-native');ROOT.mkdir(parents=True,exist_ok=True)
control=Controller()
with control.connect() as db:job=control.current(db,'deepseek')
batch=control.batch_root(job)
with sqlite3.connect(batch/'tasks.sqlite') as db:
 db.row_factory=sqlite3.Row;task=dict(db.execute("select * from tasks where state='completed' order by ordinal limit 1").fetchone())
 clicks=db.execute("select count(*) from events where event='send_click_intent_committed'").fetchone()[0]
 value=json.loads(task['result_json'])
fresh=Reader(batch).lookup(task)
assert fresh['status']=='complete' and fresh['body_markdown']==value['body_markdown'] and fresh['sources']==value['sources']
assert fresh['thinking_enabled'] is False and fresh['search_enabled'] is True
receipts=list((batch/'receipts').glob('*.json'));assert receipts
receipt=json.loads(receipts[0].read_text());assert receipt['source_device']=='deepseek-hpe14-android13' and receipt['model']=='deepseek'
assert receipt['analysis']['answer_length']==len(value['body_markdown'].strip())
assert receipt['analysis']['source_count']==len(value['sources'])
rate=json.loads(Path('/opt/monitor/geo-capture/deepseek_last_send.json').read_text())
assert 600<rate['next_send_epoch']-rate['time']<1200
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1440,'height':1000})
 context.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
 page=context.new_page();errors=[];writes=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def deny(route):
  if route.request.method=='POST':writes.append(route.request.url);route.abort()
  else:route.continue_()
 page.route('**/control/**',deny)
 page.goto('https://1any.top/geo_monitor/#capture/deepseek',wait_until='domcontentloaded',timeout=60000)
 frame=page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
 frame.locator('#dailyModels .daily-model').first.wait_for(timeout=45000)
 frame.locator('#nav .nav-item').filter(has_text='DeepSeek').click()
 assert 'DeepSeek' in frame.locator('#modelTitle').inner_text()
 assert '随机' in frame.locator('#currentSettings').inner_text()
 assert '官方安卓App' in frame.locator('#draftState').inner_text()
 assert frame.locator('#scheduleTime').input_value()=='05:00'
 assert frame.locator('#dailyModels .daily-model').count()==6
 page.screenshot(path=str(ROOT/'public-deepseek-desktop.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':900})
 page.screenshot(path=str(ROOT/'public-deepseek-mobile.png'),full_page=True)
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 assert not errors and not writes
 browser.close()
summary={'passed':True,'at':time.time(),'model':'deepseek','backend':'android','planned':63,'completed':1,'first_body_length':len(value['body_markdown']),'body_sha256':hashlib.sha256(value['body_markdown'].encode()).hexdigest(),'sources':len(value['sources']),'first_native_body_and_sources_match_receipt':True,'thinking_enabled':False,'search_enabled':True,'send_clicks':clicks,'next_interval_seconds':rate['next_send_epoch']-rate['time'],'public_desktop_mobile_pass':True,'javascript_errors':errors,'production_test_posts':writes}
(ROOT/'qa.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2));print(json.dumps(summary,ensure_ascii=False))

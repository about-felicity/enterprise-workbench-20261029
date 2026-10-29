"""Verify real first receipt, isolated clocks/counts and seven-channel public UI."""
import json
from pathlib import Path
import sqlite3
import sys
import time
import urllib.request
sys.path.insert(0,'/tmp')
sys.path.insert(0,'/home/user/redroid-deepseek-account2/code')
# LAN browser check uses the same live control-panel HTML without public auth.
from reader import Reader
from playwright.sync_api import sync_playwright

root=Path('/home/user/redroid-deepseek-account2/batches/geo-panel-deepseek2-20261017-134730-bf1a1e9e')
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 task=dict(db.execute('select * from tasks where ordinal=1').fetchone())
 assert task['state']=='completed'
 clicks=db.execute("select count(*) from events where event='send_click_intent_committed'").fetchone()[0]
 assert clicks==1
saved=json.loads(task['result_json']);native=Reader(root).lookup(task)
assert saved['body_markdown']==native['body_markdown'] and saved['sources']==native['sources']
assert saved['first_user_turn'] is True and saved['thinking_enabled'] is False and saved['search_enabled'] is True
receipt=json.loads(next((root/'receipts').glob('*.json')).read_text())
assert receipt['model']=='deepseek' and receipt['source_device']=='deepseek-hpe14-account2'
assert receipt['analysis']['answer_length']==len(native['body_markdown'].strip())
assert receipt['analysis']['source_count']==len(native['sources'])
rate=json.loads(Path('/opt/monitor/geo-capture/deepseek2_last_send.json').read_text())
assert 600<rate['next_send_epoch']-rate['time']<1200
with urllib.request.urlopen('http://127.0.0.1:8803/api/panel',timeout=20) as response:panel=json.load(response)
models={m['id']:m for m in panel['models']}
assert len(models)==7
assert models['deepseek2']['daily']['config']==models['deepseek']['daily']['config']
assert models['deepseek2']['daily']['target']==63 and models['deepseek2']['daily']['completed']==1
assert models['deepseek']['daily']['completed']>=15
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 context=browser.new_context(viewport={'width':1440,'height':1000})

 page=context.new_page();errors=[];writes=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 def guard(route):
  if route.request.method!='GET':writes.append(route.request.url);route.abort()
  else:route.continue_()
 page.route('**/*',guard)
 page.goto('http://127.0.0.1:8803/#deepseek2',wait_until='domcontentloaded',timeout=30000)
 frame=page
 frame.locator('#dailyModels .daily-model').first.wait_for(timeout=40000)
 assert frame.locator('#dailyModels .daily-model').count()==7
 frame.locator('#nav .nav-item').filter(has_text='DeepSeek 2').click()
 assert 'DeepSeek 2' in frame.locator('#modelTitle').inner_text()
 assert frame.locator('#rounds').input_value()=='3'
 assert len(frame.locator('#questions').input_value().splitlines())==21
 assert '随机' in frame.locator('#currentSettings').inner_text()
 assert frame.locator('#modelTitle img').evaluate('(e)=>e.complete && e.naturalWidth>0')
 assert not frame.locator('#connectionNotice').is_visible()
 directory=Path('/opt/monitor/geo-capture/maintenance/20261017-deepseek-account2');directory.mkdir(exist_ok=True,parents=True)
 page.screenshot(path=str(directory/'lan-second-lane-desktop.png'),full_page=True)
 page.set_viewport_size({'width':390,'height':900})
 assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
 page.screenshot(path=str(directory/'lan-second-lane-mobile.png'),full_page=True)
 assert not errors and not writes
 browser.close()
report={'passed':True,'at':time.time(),'second_lane_completed':1,'second_lane_planned':63,
 'primary_completed':models['deepseek']['daily']['completed'],'body_length':len(native['body_markdown'].strip()),
 'sources':len(native['sources']),'verified_native_matches_receipt':True,'second_account_clicks':clicks,
 'next_interval_seconds':rate['interval_seconds'],'thinking_enabled':False,'search_enabled':True,
 'lan_seven_channels':True,'javascript_errors':errors,'production_test_writes':writes}
(directory/'started-qa.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

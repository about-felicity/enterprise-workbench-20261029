"""Headless real UI / authenticated public mount / binary Word roundtrip QA."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time
import requests
sys.path[:0]=['/opt/monitor','/tmp']
from playwright.sync_api import sync_playwright
from monitor_core.cdp_chat import chrome_executable
from vps_geo_access import browser_cookie

parser=argparse.ArgumentParser();parser.add_argument('--public',action='store_true');args=parser.parse_args()
public=args.public;port=3000 if public else 3001
base='https://1any.top/geo_monitor' if public else 'http://192.168.31.106:3001'
mount='/geo_monitor' if public else ''
out=Path('/opt/monitor/geo-capture/maintenance/20261015-unified');out.mkdir(exist_ok=True)
report={'started_at':time.time(),'port':port,'public':public};errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
    context=browser.new_context(viewport={'width':1440,'height':1000})
    if public:
        unauth=requests.get(base+'/api/geo-creation/panel',allow_redirects=False,timeout=20)
        assert unauth.status_code in {302,401},unauth.status_code
        context.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','httpOnly':True,'secure':True,'sameSite':'Lax'}])
        report['public_auth_preserved']=True
    page=context.new_page();page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(base+'/#creation',wait_until='domcontentloaded',timeout=60000)
    frameui=page.frame_locator('iframe[title="GEO 内容创作控制台"]')
    frameui.locator('#product').filter().wait_for(timeout=60000)
    frameui.locator('#question option').first.wait_for(state='attached',timeout=60000)
    frame=next(f for f in page.frames if '/api/geo-creation/ui' in f.url)
    assert frameui.locator('#question').input_value()=='二硫化硒洗发水推荐'
    assert frameui.locator('[name=channel]:checked').count()==3
    assert '0.35' in frameui.locator('#limits').inner_text()
    report['creation_loaded_from_GEO_with_original_budget']=True
    result=frame.evaluate('''async(prefix)=>{const data=await(await fetch(prefix+'panel')).json();const r=await fetch(prefix+'control/new',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':data.csrf,'X-Action-Id':'914cc8dfe81d425db952e33e690b0515b'},body:JSON.stringify({date:'invalid',question:'x',max_per_category:0})});return {status:r.status,body:await r.json()}}''',mount+'/api/geo-creation/')
    assert result['status']==400,result
    report['authenticated_write_reaches_creation_validation']=True
    denied=context.request.post(base+'/api/geo-creation/control/pause',headers={'Origin':'https://foreign.test','Content-Type':'application/json'},data='{}')
    assert denied.status==403
    report['foreign_write_rejected']=True
    if public:
        mutation=frame.evaluate('''async(prefix)=>{const panel=await(await fetch(prefix+'panel')).json();const job='creation-1792060415-1e4e3a8d';const before=panel.jobs.find(j=>j.job_id===job);const results=[];for(const action of ['pause','resume']){const r=await fetch(prefix+'control/'+action,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':panel.csrf,'X-Action-Id':crypto.randomUUID().replaceAll('-','')},body:JSON.stringify({job_id:job})});results.push({action,status:r.status,ok:(await r.json()).ok})}const after=(await(await fetch(prefix+'panel')).json()).jobs.find(j=>j.job_id===job);return {results,before:before.articles.length,after:after.articles.length,paused:after.control.paused}}''',mount+'/api/geo-creation/')
        assert all(r['status']==200 and r['ok'] for r in mutation['results']),mutation
        assert mutation['before']==mutation['after']==2 and mutation['paused'] is False
        report['public_real_pause_resume_completed_acceptance_only']=True
    calls=[]
    def intercept(route):
        calls.append(json.loads(route.request.post_data));route.fulfill(status=200,content_type='application/json',body='{"ok":true,"result":{"isolated":true}}')
    page.route('**/api/geo-creation/control/new',intercept)
    frameui.locator('#new').click();frameui.locator('#message').filter(has_text='操作已完成').wait_for()
    assert len(calls)==1 and calls[0]['max_per_category']==10 and len(calls[0]['channels'])==3
    page.unroute('**/api/geo-creation/control/new',intercept)
    report['new_button_prefixed_without_extra_paid_task']=True
    links=frameui.locator('a').filter(has_text='Word')
    assert links.count()>=2
    href=links.first.get_attribute('href')
    response=context.request.get(base.split('/geo_monitor')[0]+href)
    assert response.status==200 and response.body().startswith(b'PK')
    assert hashlib.sha256(response.body()).hexdigest()==response.headers['x-content-sha256']
    report['Word_download_byte_hash_verified']=True
    if public:
        cookie=next(c for c in context.cookies() if c['name']=='geo_dashboard_creation')
        assert cookie['secure'] and cookie['httpOnly'] and cookie['path']=='/geo_monitor/api/geo-creation'
        report['creation_cookie_secure_and_prefixed']=True
    page.screenshot(path=str(out/('creation-public.png' if public else 'creation-preview.png')),full_page=True)
    page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(800)
    assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    assert frame.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
    report['mobile_no_horizontal_overflow']=True
    page.goto(base+'/#capture/yuanbao',wait_until='domcontentloaded')
    capture=page.frame_locator('iframe[title="GEO 六通道采集控制台"]')
    capture.locator('#modelTitle').filter(has_text='元宝').wait_for(timeout=60000)
    assert capture.locator('#nav .nav-item').count()==6
    report['six_capture_controls_still_loaded']=True
    assert not errors,errors
    report.update(passed=True,finished_at=time.time(),browser_errors=errors)
    browser.close()
(out/('creation-public-qa.json' if public else 'creation-preview-qa.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

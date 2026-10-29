"""Measure harmless sandbox menu taps only; never type or send a question."""
import json,sys,time,statistics
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
sys.path.insert(0,'/tmp');from vps_geo_access import browser_cookie
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-input-latency');ROOT.mkdir(exist_ok=True)
mode=sys.argv[1]
url='http://127.0.0.1:3000/api/geo-capture/login/deepseek_test/' if 'lan' in mode else 'https://1any.top/geo_monitor/api/geo-capture/login/deepseek_test/'
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
 c=b.new_context(viewport={'width':390,'height':844},permissions=['local-network-access'])
 if 'lan' not in mode:c.add_cookies([{'name':'geo_monitor_session','value':browser_cookie(),'domain':'1any.top','path':'/geo_monitor/','secure':True,'httpOnly':True,'sameSite':'Lax'}])
 page=c.new_page();page.goto(url+'ui',wait_until='domcontentloaded',timeout=60000)
 page.wait_for_function("document.getElementById('screen').naturalWidth>0&&csrf.length===64",timeout=30000,polling=100)
 # Watch only the top navigation pixels; no screenshot/account information is exported.
 page.evaluate("""()=>{window.probeCanvas=document.createElement('canvas');probeCanvas.width=72;probeCanvas.height=128;window.probeHash=()=>{const x=probeCanvas.getContext('2d',{willReadFrequently:true});x.drawImage(document.getElementById('screen'),0,0,72,128);const a=x.getImageData(0,8,72,25).data;let h=0;for(let i=0;i<a.length;i+=4)h+=a[i];return h};}""")
 results=[]
 try:
  for index in range(4):
   # Alternating top-left menu tap and outside-panel tap closes the sidebar.
   x,y=(48,100) if index%2==0 else (680,600)
   value=page.evaluate("""async ({x,y})=>{const before=probeHash();const start=performance.now();const r=await fetch(prefix+'input',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf,'X-Action-Id':key()},body:JSON.stringify({type:'click',x,y,flow})});return {ok:r.ok,ack:performance.now()-start,hash:before,start};}""",{'x':x,'y':y})
   assert value['ok']
   page.evaluate('(h)=>window.baseline=h',value['hash'])
   try:
    page.wait_for_function('Math.abs(probeHash()-window.baseline)>500',timeout=8000,polling=20)
    visible=page.evaluate('(t)=>performance.now()-t',value['start'])
   except Exception:visible=None
   results.append({'ack_ms':round(value['ack'],1),'visible_ms':round(visible,1) if visible is not None else None})
   page.wait_for_timeout(300)
 finally:
  # Return to the same App activity without logging out or changing any account setting.
  import subprocess
  subprocess.run(['docker','exec','deepseek-manual-test','am','start','-W','-n','com.deepseek.chat/.MainActivity'],capture_output=True,timeout=20)
  b.close()
report={'mode':mode,'at':time.time(),'method':'sandbox menu taps through actual public input and video; no text/questions','samples':results}
(ROOT/(mode+'.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report))

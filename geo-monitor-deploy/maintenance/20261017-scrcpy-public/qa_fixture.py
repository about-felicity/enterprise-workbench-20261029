"""Live read-only scrcpy video plus isolated login/input state transitions."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import sys
import threading
import time
from urllib.parse import urlsplit,parse_qs
sys.path.insert(0,'/opt/monitor/geo-capture')
from scrcpy_stream import ScrcpyStream
from deepseek_android_login import validate_input
from playwright.sync_api import sync_playwright,expect

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-scrcpy-public')
states={m:'waiting_login' for m in ['deepseek','deepseek2']};videos={};inputs=[]
flows={'deepseek':'b'*32,'deepseek2':'c'*32};csrf='a'*64
for model in states:videos[model]=ScrcpyStream(model,control=False).start()
class Handler(BaseHTTPRequestHandler):
 def send(self,data,mime='application/json',code=200):
  if not isinstance(data,bytes):data=json.dumps(data).encode()
  self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(data)
 def do_GET(self):
  parts=urlsplit(self.path).path.split('/');model=parts[-2] if len(parts)>2 else None;part=parts[-1]
  if self.path=='/':
   self.send(b'<button onclick="window.open(\'/api/login/deepseek/ui\')">primary</button><button onclick="window.open(\'/api/login/deepseek2/ui\')">second</button>','text/html');return
  if model not in states:self.send({},code=404);return
  if part=='ui':self.send(Path('/opt/monitor/geo-capture/deepseek_login.html').read_bytes(),'text/html');return
  if part=='state':self.send({'id':flows[model],'status':states[model],'csrf':csrf,'message':{'risk_blocked':'账号已封禁，请处理','verification_required':'需要人工验证','verifying':'正在复核','ready':'正常登录确认'}.get(states[model],'请手动登录'),'backend':'scrcpy'});return
  if part=='stream':
   if parse_qs(urlsplit(self.path).query).get('flow')!=[flows[model]]:self.send({},code=403);return
   self.send_response(200);self.send_header('Content-Type','multipart/x-mixed-replace; boundary=scrcpy');self.send_header('Cache-Control','no-store');self.end_headers()
   try:
    for block in videos[model].frames():
     if states[model]=='ready':break
     self.wfile.write(block);self.wfile.flush()
   except (BrokenPipeError,ConnectionResetError):pass
   return
  self.send({},code=404)
 def do_POST(self):
  model=self.path.split('/')[-2];value=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  if model not in states or self.headers.get('X-CSRF-Token')!=csrf or value.pop('flow',None)!=flows[model]:self.send({},code=403);return
  kind,payload=validate_input(value);inputs.append({'model':model,'kind':kind,'payload':payload});self.send({'ok':True})
 def log_message(self,*_):pass
server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
results=[]
try:
 with sync_playwright() as p:
  browser=p.chromium.launch(executable_path='/usr/bin/google-chrome',headless=True,args=['--no-sandbox'])
  for model,mobile in [('deepseek',False),('deepseek2',True)]:
   context=browser.new_context(viewport={'width':390 if mobile else 540,'height':844 if mobile else 920},is_mobile=mobile,has_touch=mobile,permissions=['local-network-access'])
   page=context.new_page();page.goto('http://127.0.0.1:'+str(server.server_port)+'/')
   with context.expect_page() as opened:page.get_by_text('second' if mobile else 'primary',exact=True).click()
   popup=opened.value;popup.bring_to_front();errors=[];popup.on('pageerror',lambda e:errors.append(str(e)))
   expect(popup.locator('#screen')).to_be_visible()
   try:popup.wait_for_function('document.getElementById("screen").naturalWidth===432',timeout=20000,polling=100)
   except Exception:
    print(json.dumps({'model':model,'text':popup.locator('body').inner_text(),'video_stopped':videos[model].stopped.is_set(),'video_frames':videos[model].sequence,'errors':errors,'image':popup.locator('#screen').evaluate('(e)=>({src:e.src,width:e.naturalWidth,complete:e.complete})')},ensure_ascii=False));raise
   assert popup.evaluate('document.documentElement.scrollWidth<=innerWidth')
   popup.locator('#screen').tap() if mobile else popup.locator('#screen').click()
   popup.locator('#textInput').fill('123456');popup.locator('#send').click()
   popup.wait_for_timeout(200)
   assert any(v['model']==model and v['kind']=='text' and v['payload']=='123456' for v in inputs)
   assert any(v['model']==model and v['kind']=='touch' for v in inputs)
   states[model]='risk_blocked';expect(popup.locator('#message')).to_contain_text('封禁',timeout=4000);assert not popup.is_closed()
   states[model]='verification_required';expect(popup.locator('#message')).to_contain_text('人工验证',timeout=4000);assert not popup.is_closed()
   popup.screenshot(path=str(ROOT/('fixture-mobile.png' if mobile else 'fixture-desktop.png')),full_page=True)
   states[model]='verifying';expect(popup.locator('#message')).to_contain_text('复核',timeout=4000);assert not popup.is_closed()
   states[model]='ready'
   popup.wait_for_event('close',timeout=5000)
   assert not errors
   results.append({'model':model,'mobile':mobile,'actual_scrcpy_frames':videos[model].sequence,'fixture_control_validated':True,'risk_and_verification_did_not_close':True,'verifying_did_not_close':True,'ready_closed_popup':True,'no_overflow':True,'native_input_sent':False})
   context.close()
  browser.close()
 report={'passed':True,'at':time.time(),'scenarios':results,'production_login_or_send_actions':0,'native_capture_control':False}
 (ROOT/'qa-fixture.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
finally:
 server.shutdown();server.server_close()
 for v in videos.values():v.close()

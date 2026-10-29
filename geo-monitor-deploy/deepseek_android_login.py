"""Short lived authenticated Android screen relay; account data stays in /data."""
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
import fcntl,hmac,io,json,sys,threading,time
from pathlib import Path

WIDTH,HEIGHT=720,1280

def validate_input(value):
 kind=value.get('type')
 if kind=='batch':
  events=value.get('events')
  if not isinstance(events,list) or not 1<=len(events)<=16:raise ValueError('无效输入批次')
  if any(not isinstance(e,dict) or e.get('type')=='batch' for e in events):raise ValueError('无效输入批次')
  return kind,[validate_input(e) for e in events]
 if kind=='click':
  x,y=value.get('x'),value.get('y')
  if type(x) not in (int,float) or type(y) not in (int,float) or not(0<=x<WIDTH and 0<=y<HEIGHT):raise ValueError('无效点击位置')
  return kind,(int(x),int(y))
 if kind=='text':
  text=value.get('text')
  if not isinstance(text,str) or not 1<=len(text)<=4096 or '\x00' in text:raise ValueError('无效输入')
  return kind,text
 if kind=='touch':
  action,x,y=value.get('action'),value.get('x'),value.get('y')
  if type(action)!=int or action not in (0,1,2) or type(x) not in (int,float) or type(y) not in (int,float) or not(0<=x<WIDTH and 0<=y<HEIGHT):raise ValueError('无效触摸')
  return kind,(action,int(x),int(y))
 if kind=='scroll':
  delta=value.get('delta')
  if type(delta) not in (int,float) or not -1000<=delta<=1000:raise ValueError('无效滚动')
  return kind,delta
 if kind=='key':
  keys={'Enter':66,'Tab':61,'Backspace':67,'Delete':112,'Escape':4,'ArrowLeft':21,'ArrowRight':22,'ArrowUp':19,'ArrowDown':20,'Home':122,'End':123}
  if value.get('key')=='a' and value.get('modifiers',0)&2:return kind,('ctrl',29)
  if value.get('key') not in keys:raise ValueError('不支持的按键')
  return kind,keys[value['key']]
 raise ValueError('不支持的操作')

def main(path):
 request=json.loads(path.read_text());target=path.with_name('state.json');lock=threading.RLock()
 model=request.get('model','deepseek')
 testing=model=='deepseek_test'
 if not testing:
  runtime={'deepseek':'redroid-deepseek','deepseek2':'redroid-deepseek-account2'}[model]
  sys.path.insert(0,'/home/user/'+runtime+'/code')
  from device import device,auth,PACKAGE,shell
  from android import Android
 from scrcpy_stream import ScrcpyStream
 from deepseek_auth_monitor import record
 state={k:request[k] for k in ('id','batch','revision','created_at','expires_at')}
 state.update(backend='scrcpy',model=model,status='opening')
 def publish(status,message):
  state.update(status=status,message=message,updated_at=time.time());tmp=target.with_suffix('.tmp');tmp.write_text(json.dumps(state,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(target)
 publish('opening','正在建立scrcpy实时投屏…')
 account=Path('/opt/monitor/geo-capture/'+model+'_account.lock').open('a')
 try:fcntl.flock(account,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BlockingIOError:
  account.close();publish('failed','当前App仍有问题正在采集，等待完成后再打开登录');return
 if testing:
  import subprocess
  from scrcpy_stream import ADB,SERIALS
  try:
   for attempt in range(4):
    # Only this sandbox serial is reconnected after its Android restart.
    subprocess.run([ADB,'disconnect',SERIALS[model]],capture_output=True,timeout=10)
    subprocess.run([ADB,'connect',SERIALS[model]],check=True,capture_output=True,timeout=20)
    launch=subprocess.run([ADB,'-s',SERIALS[model],'shell','am','start','-W','-n','com.deepseek.chat/.MainActivity'],capture_output=True,timeout=30)
    if launch.returncode==0:break
    time.sleep(2)
   else:raise RuntimeError('Test device not ready')
  except Exception:
   publish('failed','测试机尚未就绪，请稍后点击重开；账号数据保留');account.close();return
 else:d=device();shell('am','start','-W','-n',PACKAGE+'/.MainActivity')
 try:video=ScrcpyStream(model).start()
 except Exception:
  publish('failed','scrcpy投屏暂不可用，请稍后重开；账号数据保留');account.close();return
 allowed_states={'waiting_login','risk_blocked','verification_required','verifying'}
 class Handler(BaseHTTPRequestHandler):
  disable_nagle_algorithm=True
  def respond(self,value,mime='application/json',code=200):
   if not isinstance(value,bytes):value=json.dumps(value).encode()
   self.send_response(code);self.send_header('Content-Type',mime);self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(value)));self.end_headers();self.wfile.write(value)
  def allowed(self):return hmac.compare_digest(self.headers.get('X-Login-Token',''),request['token'])
  def do_GET(self):
   if not self.allowed():self.respond({'ok':False},code=403);return
   try:
    with lock:
     if self.path=='/state':self.respond({**state,'frames':video.sequence,'last_frame_at':video.last_frame});return
     if self.path not in {'/stream','/frame'} or state['status'] not in allowed_states:self.respond({'ok':False},code=409);return
     if self.path=='/frame':self.respond(video.jpeg,'image/jpeg');return
    self.send_response(200);self.send_header('Content-Type','multipart/x-mixed-replace; boundary=scrcpy');self.send_header('Cache-Control','no-store');self.send_header('X-Accel-Buffering','no');self.send_header('Connection','close');self.end_headers()
    for frame in video.frames():
     if state['status'] not in allowed_states:break
     self.wfile.write(frame);self.wfile.flush()
   except Exception:self.respond({'ok':False},code=503)
  def do_POST(self):
   if not self.allowed():self.respond({'ok':False},code=403);return
   try:
    size=int(self.headers.get('Content-Length',0))
    if self.path!='/input' or not 0<size<=20000:raise ValueError('无效输入')
    kind,params=validate_input(json.loads(self.rfile.read(size)))
    with lock:
     if state['status'] not in allowed_states or state['status']=='verifying':self.respond({'ok':False},code=409);return
     video.input(kind,params)
     self.respond({'ok':True})
   except ValueError:self.respond({'ok':False},code=400)
   except Exception:self.respond({'ok':False,'message':'输入结果未确认，请查看画面后再操作'},code=503)
  def log_message(self,*_):pass
 server=ThreadingHTTPServer(('127.0.0.1',request.get('port',8815)),Handler)
 threading.Thread(target=server.serve_forever,daemon=True).start()
 publish('waiting_login','scrcpy投屏已连接，请手动登录；电脑可点击输入，手机可触摸并使用下方输入框')
 ready_count=0
 try:
  while time.time()<request['expires_at']:
   if testing:
    # Manual sandbox: never inspect answers, send questions, alter modes or auto-close after login.
    time.sleep(2);continue
   with lock:result=auth(d)
   if result['status']=='ready':
    ready_count+=1
    if ready_count>=2:
     with lock:publish('verifying','正在检查正常对话界面及搜索模式；有风险或封禁提示不会通过')
     try:
      with lock:Android().ready();result=auth(d)
      if result['status']!='ready':raise ValueError('not ready')
     except Exception:
      ready_count=0
      with lock:publish(result['status'] if result['status'] in allowed_states else 'waiting_login',result.get('message','正常对话界面尚未就绪'))
      time.sleep(2);continue
     record(model,result)
     health=Path('/opt/monitor/geo-capture/'+model+'_app_session.json');tmp=health.with_suffix('.tmp');tmp.write_text(json.dumps({'status':'ready','checked_at':time.time(),'last_checkpoint':time.time(),'backend':'android'}));tmp.chmod(0o600);tmp.replace(health)
     with lock:publish('ready','账号及正常对话校验已通过，scrcpy已关闭，正在恢复原任务')
     video.close();account.close();time.sleep(5);return
   else:
    ready_count=0
    if result['status'] in {'login_required','risk_blocked','verification_required'}:
     record(model,result)
     with lock:publish('waiting_login' if result['status']=='login_required' else result['status'],result['message'])
   time.sleep(2)
  publish('failed','登录窗口已过期，可重新打开；App保存的账号数据保留')
 finally:video.close();account.close();server.shutdown()

if __name__=='__main__':main(Path(sys.argv[1]))

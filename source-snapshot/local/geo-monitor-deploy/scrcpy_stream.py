"""scrcpy 5.0 video/control bridge. No screenshots, accounts or API questions."""
import socket
import struct
import subprocess
import threading
import time
import secrets
from pathlib import Path

ADB='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
SERVER=Path('/opt/monitor/geo-capture/vendor/scrcpy-server-v5.0')
SERIALS={'deepseek':'127.0.0.1:5560','deepseek2':'127.0.0.1:5561','deepseek_test':'127.0.0.1:5562'}
WIDTH,HEIGHT=720,1280

def touch_packet(action,x,y):
 if action not in (0,1,2) or not 0<=x<WIDTH or not 0<=y<HEIGHT:raise ValueError('无效触摸')
 return struct.pack('>BBqiiHHHII',2,action,-2,int(x),int(y),WIDTH,HEIGHT,0 if action==1 else 65535,0,0)

def key_packets(code,modifiers=0):
 return b''.join(struct.pack('>BBIII',0,action,code,0,modifiers) for action in (0,1))

class ScrcpyStream:
 def __init__(self,model,control=True):
  if model not in SERIALS:raise ValueError('无效通道')
  self.model=model;self.serial=SERIALS[model];self.control_enabled=control
  self.stopped=threading.Event();self.changed=threading.Condition();self.jpeg=None;self.sequence=0
  self.last_frame=0;self.received_bytes=0;self.first_bytes=b'';self.control_lock=threading.Lock();self.video=None;self.control=None;self.encoder=None;self.process=None;self.port=None
 def adb(self,*args):
  return subprocess.check_output([ADB,'-s',self.serial,*args],timeout=20,stderr=subprocess.DEVNULL).decode().strip()
 def start(self):
  if not SERVER.is_file():raise RuntimeError('scrcpy server missing')
  self.adb('push',str(SERVER),'/data/local/tmp/geo-scrcpy-server-v5.jar')
  scid=secrets.randbelow(0x7fffffff)
  self.port=int(self.adb('forward','tcp:0',f'localabstract:scrcpy_{scid:08x}'))
  args=[ADB,'-s',self.serial,'shell','CLASSPATH=/data/local/tmp/geo-scrcpy-server-v5.jar','app_process','/','com.genymobile.scrcpy.Server','5.0',f'scid={scid:08x}','log_level=error','audio=false',f'control={str(self.control_enabled).lower()}','tunnel_forward=true','raw_stream=true','send_dummy_byte=true','max_size=1280','max_fps=10','video_bit_rate=1500000','clipboard_autosync=false','power_on=false','cleanup=true']
  self.process=subprocess.Popen(args,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  try:
   until=time.monotonic()+12
   while True:
    try:
     candidate=socket.create_connection(('127.0.0.1',self.port),timeout=2)
     if candidate.recv(1)!=b'\x00':candidate.close();raise OSError('server not listening yet')
     self.video=candidate;break
    except OSError:
     if time.monotonic()>until or self.process.poll() is not None:raise RuntimeError('scrcpy video unavailable')
     time.sleep(.15)
   if self.control_enabled:
    self.control=socket.create_connection(('127.0.0.1',self.port),timeout=3)
    self.control.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
   self.video.settimeout(20)
   self.encoder=subprocess.Popen(['/usr/bin/ffmpeg','-nostdin','-hide_banner','-loglevel','error','-probesize','32','-analyzeduration','0','-flags','low_delay','-threads','1','-f','h264','-i','pipe:0','-an','-vf','scale=432:-2','-threads','1','-q:v','6','-vsync','0','-flush_packets','1','-f','image2pipe','-vcodec','mjpeg','pipe:1'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,bufsize=0)
   threading.Thread(target=self._feed,daemon=True).start();threading.Thread(target=self._frames,daemon=True).start()
   with self.changed:
    if not self.changed.wait_for(lambda:self.jpeg is not None or self.stopped.is_set(),timeout=18) or not self.jpeg:raise RuntimeError('scrcpy decoding unavailable')
   return self
  except Exception:self.close();raise
 def _feed(self):
  try:
   while not self.stopped.is_set():
    try:block=self.video.recv(65536)
    except socket.timeout:continue  # A static Android screen legitimately sends no new video packets.
    if not block:break
    self.received_bytes+=len(block)
    if not self.first_bytes:self.first_bytes=block[:12]
    pending=memoryview(block)
    while pending:
     written=self.encoder.stdin.write(pending)
     if not written:raise OSError('video pipe closed')
     pending=pending[written:]
  except (OSError,ValueError):pass
  finally:
   try:self.encoder.stdin.close()
   except Exception:pass
 def _frames(self):
  buf=b''
  try:
   while not self.stopped.is_set():
    block=self.encoder.stdout.read(32768)
    if not block:break
    buf+=block
    if len(buf)>4_000_000:raise ValueError('video frame overflow')
    while True:
     begin=buf.find(b'\xff\xd8');end=buf.find(b'\xff\xd9',max(0,begin))
     if begin<0 or end<0:break
     jpeg=buf[begin:end+2];buf=buf[end+2:]
     with self.changed:self.jpeg=jpeg;self.sequence+=1;self.last_frame=time.time();self.changed.notify_all()
  finally:
   self.stopped.set()
   with self.changed:self.changed.notify_all()
 def frames(self):
  previous=0
  prefix=b'--scrcpy\r\n'
  while not self.stopped.is_set():
   with self.changed:
    self.changed.wait_for(lambda:self.sequence!=previous or self.stopped.is_set(),timeout=2)
    if self.stopped.is_set():break
    if not self.jpeg:continue
    previous=self.sequence;jpeg=self.jpeg
   # Close each part immediately, including a final static frame; browsers need not wait for another Android update.
   yield prefix+b'Content-Type: image/jpeg\r\nContent-Length: '+str(len(jpeg)).encode()+b'\r\n\r\n'+jpeg+b'\r\n--scrcpy\r\n'
   prefix=b''
 def send(self,data):
  if not self.control or self.stopped.is_set():raise RuntimeError('scrcpy control closed')
  with self.control_lock:self.control.sendall(data)
 def input(self,kind,value):
  if kind=='batch':
   for part,params in value:self.input(part,params)
  elif kind=='click':
   x,y=value;self.send(touch_packet(0,x,y)+touch_packet(1,x,y))
  elif kind=='touch':self.send(touch_packet(*value))
  elif kind=='text':
   data=value.encode('utf-8')
   if len(data)>16384:raise ValueError('输入过长')
   if value.isascii():
    for offset in range(0,len(data),300):
     part=data[offset:offset+300];self.send(struct.pack('>BI',1,len(part))+part)
    return
   # Official set-clipboard/paste control supports Unicode including Chinese.
   self.send(struct.pack('>BQBI',9,0,1,len(data))+data)
  elif kind=='scroll':
   down=value>0
   for i in range(9):
    y=int((900 if down else 400)+(i/8)*( -500 if down else 500))
    self.send(touch_packet(0 if i==0 else 1 if i==8 else 2,360,y));time.sleep(.025)
  elif kind=='key':self.send(key_packets(value if isinstance(value,int) else 29,0 if isinstance(value,int) else 4096))
  else:raise ValueError('无效控制')
 def close(self):
  self.stopped.set()
  for conn in (self.video,self.control):
   if conn:
    try:conn.shutdown(socket.SHUT_RDWR);conn.close()
    except OSError:pass
  for proc in (self.encoder,self.process):
   if proc and proc.poll() is None:
    proc.terminate()
    try:proc.wait(timeout=4)
    except subprocess.TimeoutExpired:proc.kill();proc.wait(timeout=3)
  if self.port:
   try:self.adb('forward','--remove','tcp:'+str(self.port))
   except Exception:pass
  with self.changed:self.changed.notify_all()

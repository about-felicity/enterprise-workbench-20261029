import importlib.util
import json
from pathlib import Path
import time
spec=importlib.util.spec_from_file_location('scrcpy_candidate','/tmp/geo-scrcpy-stream-candidate.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
results=[]
original_popen=m.subprocess.Popen
debug=Path('/tmp/geo-scrcpy-video-debug.log').open('wb');Path(debug.name).chmod(0o600)
def popen(*args,**kwargs):
 kwargs['stderr']=debug
 if 'app_process' in args[0]:kwargs['stdout']=debug
 return original_popen(*args,**kwargs)
m.subprocess.Popen=popen
for model in ['deepseek','deepseek2']:
 started=time.time();s=m.ScrcpyStream(model,control=False)
 try:
  s.start();Path('/tmp/'+model+'-scrcpy-proof.jpg').write_bytes(s.jpeg)
  time.sleep(1);results.append({'model':model,'frames':s.sequence,'first_frame_seconds':round(time.time()-started,2),'jpeg_bytes':len(s.jpeg),'control_enabled':False,'source':'official scrcpy-server 5.0 H264 -> ffmpeg JPEG stream'})
 except Exception:
  print(json.dumps({'received_bytes':s.received_bytes,'codec_prefix':s.first_bytes.hex(),'frames':s.sequence}));raise
 finally:s.close()
print(json.dumps(results))

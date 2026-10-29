import json,sys,tempfile,unittest,socket,os
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,os.environ.get('GEO_TEST_CODE','/opt/monitor/geo-capture'))
import manual_login
from scrcpy_stream import SERIALS,ScrcpyStream
from control_panel import MODELS
from deepseek_auth_monitor import CHANNELS

class SandboxTests(unittest.TestCase):
 def test_idle_video_timeout_does_not_close_feed(self):
  class Video:
   def __init__(self):self.count=0
   def recv(self,_):
    self.count+=1
    if self.count==1:raise socket.timeout()
    return b'data' if self.count==2 else b''
  class Sink:
   def __init__(self):self.data=b''
   def write(self,data):self.data+=bytes(data);return len(data)
   def close(self):pass
  s=ScrcpyStream('deepseek_test');s.video=Video();sink=Sink();s.encoder=SimpleNamespace(stdin=sink)
  s._feed();self.assertEqual(sink.data,b'data');self.assertEqual(s.received_bytes,4)
 def test_cached_video_frame_keeps_static_stream_alive(self):
  s=ScrcpyStream('deepseek_test');s.jpeg=b'jpeg';s.sequence=1
  with patch.object(s.changed,'wait_for',return_value=False):
   frames=s.frames();first=next(frames);second=next(frames)
   self.assertTrue(first.startswith(b'--scrcpy\r\nContent-Type:'))
   self.assertTrue(second.startswith(b'Content-Type:'))
   self.assertTrue(first.endswith(b'jpeg\r\n--scrcpy\r\n'))
   self.assertTrue(second.endswith(b'jpeg\r\n--scrcpy\r\n'))
   s.stopped.set();frames.close()
 def test_manual_only(self):
  self.assertEqual(SERIALS['deepseek_test'],'127.0.0.1:5562')
  self.assertNotIn('deepseek_test',MODELS)
  self.assertNotIn('deepseek_test',CHANNELS)
 def test_test_start_has_own_state_port_and_deadline(self):
  with tempfile.TemporaryDirectory() as d,patch('manual_login.subprocess.run') as run:
   state=manual_login.start(d,'/home/user/redroid-deepseek-test','manual-test',0,model='deepseek_test')
   value=json.loads((Path(d)/'manual-login/deepseek_test/request.json').read_text())
   self.assertEqual(value['port'],8817);self.assertEqual(value['backend'],'android')
   self.assertAlmostEqual(value['expires_at']-value['created_at'],3600,places=2)
   self.assertIn('--property=RuntimeMaxSec=3660',run.call_args.args[0]);self.assertEqual(state['status'],'opening')
   self.assertFalse((Path(d)/'manual-login/deepseek/request.json').exists())
 def test_state_missing_and_invalid_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   self.assertEqual(manual_login.state(d,'deepseek_test')['status'],'closed')
   with self.assertRaises(ValueError):manual_login.state(d,'anything')

if __name__=='__main__':unittest.main()

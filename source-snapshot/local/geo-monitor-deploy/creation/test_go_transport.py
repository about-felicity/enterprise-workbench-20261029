import http.server,json,os,socketserver,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
import requests
from .go_transport import GoSession
from .client import CreationClient
from . import materials

class NativeTransportTests(unittest.TestCase):
 def test_unix_socket_handoff_preserves_response_and_no_secret_headers(self):
  with tempfile.TemporaryDirectory() as folder:
   received=[]
   class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
     body=self.rfile.read(int(self.headers['Content-Length']));received.append((self.path,self.headers.get('Authorization'),json.loads(body)))
     self.send_response(429);self.end_headers();self.wfile.write(b'{"error":"rate_limit"}')
    def log_message(self,*args):pass
   server=socketserver.UnixStreamServer(str(Path(folder)/'model.sock'),Handler)
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    response=GoSession(str(Path(folder)/'model.sock')).post('https://api.deepseek.com/chat/completions',json={'prompt':'测试'},headers={'Authorization':'REDACTED_CONFIGURE_LOCALLY'})
    self.assertEqual(response.status_code,429);self.assertEqual(response.json(),{'error':'rate_limit'})
    self.assertEqual(received,[('/completions',None,{'prompt':'测试'})])
   finally:server.shutdown();server.server_close();thread.join()
 def test_missing_native_service_does_not_fallback_or_resend(self):
  with tempfile.TemporaryDirectory() as folder,patch('requests.Session') as fallback:
   with self.assertRaises(requests.RequestException):GoSession(str(Path(folder)/'absent')).post('https://api.deepseek.com/chat/completions',json={})
   fallback.assert_not_called()
 def test_explicit_fixture_session_is_preserved(self):
  with tempfile.TemporaryDirectory() as folder:
   key=Path(folder)/'key';key.write_text('sk-'+'x'*24);session=object()
   with patch.dict(os.environ,{'GEO_CREATION_MODEL_SOCKET':'unused'}):
    self.assertIs(CreationClient(key,session=session).session,session)
    self.assertIsInstance(CreationClient(key).session,GoSession)
 def test_dynamic_search_locks_and_rate_are_per_plan_and_channel(self):
  with tempfile.TemporaryDirectory() as folder,patch.object(materials,'CONTENT_BASE',Path(folder)):
   materials.atomic_json(Path(folder)/'creation_search_pool.json',{'enabled':True})
   locks=[];rates=[]
   for i in range(10):
    root=Path(folder)/('plan-'+str(i));materials.atomic_json(root/'settings.json',{'studio_plan':{'plan_id':root.name}})
    with patch.object(materials,'ROOT',root):
     for model in ('baidu_ai','wenxin_card'):
      r=materials.search_resources(model);self.assertTrue(r['dedicated']);locks.append(r['lock']);rates.append(r['rate'])
     self.assertFalse(materials.search_resources('deepseek')['dedicated'])
   self.assertEqual(len(set(locks)),20);self.assertEqual(len(set(rates)),20)

if __name__=='__main__':unittest.main()

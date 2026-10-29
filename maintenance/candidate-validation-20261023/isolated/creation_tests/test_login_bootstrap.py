import json,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
import requests
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fleet_status as fleet

class LoginBootstrapTests(unittest.TestCase):
 def test_login_bootstraps_without_querying_tasks_and_state_requires_session(self):
  with tempfile.TemporaryDirectory() as temp:
   base=Path(temp);(base/'deepseek_login.html').write_text('<title>fixture login</title>')
   server=fleet.ThreadingHTTPServer(('127.0.0.1',0),fleet.Handler)
   thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
   try:
    with patch.object(fleet,'BASE',base),patch.object(fleet,'controller',side_effect=AssertionError('Heavy panel must not run')),patch('manual_login.relay',return_value=(200,'application/json',b'{"status":"waiting_login"}')):
     url='http://127.0.0.1:'+str(server.server_port)
     client=requests.Session();client.trust_env=False
     self.assertEqual(client.get(url+'/api/login/state').status_code,403)
     response=client.get(url+'/api/login/ui');self.assertEqual(response.status_code,200)
     token=client.cookies.get('geo_control');self.assertEqual(len(token),64)
     self.assertIn('HttpOnly',response.headers['Set-Cookie']);self.assertIn('SameSite=Strict',response.headers['Set-Cookie'])
     response=client.get(url+'/api/login/state');self.assertEqual(response.json()['csrf'],token)
     self.assertEqual(response.json()['status'],'waiting_login')
   finally:server.shutdown();server.server_close();thread.join()

if __name__=='__main__':unittest.main()

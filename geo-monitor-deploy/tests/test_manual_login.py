import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import unittest
import json
import socket
import tempfile
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch
import requests
from deepseek_login_ui import validate_input
import deepseek_login_ui

class ManualInputTests(unittest.TestCase):
    def test_only_bounded_direct_user_input_is_accepted(self):
        self.assertEqual(validate_input({'type':'click','x':20,'y':30})[0],'click')
        self.assertEqual(validate_input({'type':'text','text':'test-only'})[1],{'text':'test-only'})
        self.assertEqual(validate_input({'type':'key','key':'Tab'})[1]['windowsVirtualKeyCode'],9)
        for value in [{'type':'click','x':-1,'y':1},{'type':'click','x':1100,'y':1},
                      {'type':'text','text':'x'*4097},{'type':'navigate','url':'https://other.example'},
                      {'type':'evaluate','expression':'anything'},{'type':'key','key':'F12'}]:
            with self.assertRaises(ValueError):validate_input(value)

    def test_manual_login_closes_browser_then_checks_new_session_before_ready(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'geo-source-card-collectors'))
        logged=threading.Event();checking=threading.Event();allow_ready=threading.Event()
        instances=[];calls=[]
        class FakePage:
            def call(self,method,params=None):
                calls.append(method)
                if method=='Network.getAllCookies':return {'cookies':[{'name':'test-cookie'}] if logged.is_set() else []}
                if method=='Input.insertText':logged.set()
                return {}
        class FakeCollector:
            def __init__(self,*args,**kwargs):self.page=FakePage();self.closed=False;instances.append(self)
            def navigate_home(self):pass
            def session_status(self):return {'ok':logged.is_set()}
            def close(self):self.closed=True
            def check_ready(self):
                checking.set();allow_ready.wait(5)
                return {'ok':True}
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            request=root/'request.json'
            request.write_text(json.dumps({'id':'flow','batch':'test-batch','revision':3,'runtime':str(root/'runtime'),
                                           'token':'private-fixture-token'}))
            with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
            def state():
                try:return json.loads((root/'state.json').read_text())
                except (FileNotFoundError,json.JSONDecodeError):return {}
            with patch.dict(sys.modules,{'web_collectors.collector':SimpleNamespace(BrowserCollector=FakeCollector)}),patch.dict('os.environ'):
                thread=threading.Thread(target=deepseek_login_ui.main,args=(request,),
                                        kwargs={'port':port,'linger':.01,'poll_seconds':.02},daemon=True)
                thread.start()
                deadline=time.time()+5
                while state().get('status')!='waiting_login' and time.time()<deadline:time.sleep(.02)
                http=requests.Session();http.trust_env=False
                base='http://127.0.0.1:'+str(port)
                self.assertEqual(http.get(base+'/state',timeout=2).status_code,403)
                self.assertEqual(http.post(base+'/input',json={'type':'text','text':'fixture-only'},
                    headers={'X-Login-Token':'private-fixture-token'},timeout=2).status_code,200)
                self.assertTrue(checking.wait(5))
                self.assertTrue(instances[0].closed)
                self.assertEqual(state()['status'],'verifying')
                allow_ready.set();thread.join(timeout=5)
                self.assertFalse(thread.is_alive())
                self.assertEqual(state()['status'],'ready')
                self.assertTrue(all(instance.closed for instance in instances))
                self.assertNotIn('fixture-only',(root/'state.json').read_text())
                self.assertNotIn('private-fixture-token',(root/'state.json').read_text())
                self.assertFalse(any(method in calls for method in ['Runtime.evaluate','Input.dispatchKeyEvent']))

if __name__=='__main__':unittest.main()

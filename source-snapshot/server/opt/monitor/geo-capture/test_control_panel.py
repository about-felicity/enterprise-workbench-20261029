import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
import uuid
from http.server import ThreadingHTTPServer
import threading
from unittest.mock import patch
import requests

from control_panel import Controller,Conflict,MODELS,atomic,read,validate


class FakeSystem:
    def __init__(self):self.states={};self.starts=[];self.enabled=[];self.fail=False
    def state(self,service):return self.states.get(service,'inactive')
    def start(self,service):
        self.starts.append(service)
        if self.fail:raise OSError('uncertain start')
        self.states[service]='active'
    def enable_current(self,service,old):self.enabled.append((service,old))


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.system=FakeSystem()
        fleet={'containers':[],'collectors':[]}
        for model,meta in MODELS.items():
            batch='old-'+model
            health=self.root/'batches'/batch/'bridge_health.json'
            atomic(health,{'status':'complete','captured':2,'processed':2,'geo_processed':2,'batch':batch,'planned':2})
            fleet['collectors'].append({'name':meta['name'],'health':str(health),'service':'old-'+model+'.service','planned':2})
            if meta['kind']=='web':atomic(self.root/'config'/(model+'.json'),{'model':model,'batch':batch,'questions':['问题一','问题二'],'rounds':meta['rounds']})
        atomic(self.root/'fleet.json',fleet)
        self.control=Controller(self.root,self.system,self.root/'native')

    def tearDown(self):self.temp.cleanup()
    def key(self):return uuid.uuid4().hex
    def current(self,model):return next(m for m in self.control.all()['models'] if m['id']==model)
    def act(self,model,action,value=None,key=None):return self.control.action(model,action,value or {},key or self.key())

    def test_settings_edit_is_separate_from_immutable_current(self):
        old=self.current('wenxin_card')['current']['config']
        self.act('wenxin_card','settings',{'questions':['新问题'],'rounds':2,'interval':90,'revision':1})
        state=self.current('wenxin_card')
        self.assertEqual(state['current']['config'],old)
        self.assertEqual(state['settings']['questions'],['新问题'])
        with self.assertRaises(Conflict):self.act('wenxin_card','settings',{'questions':['旧版本'],'rounds':2,'interval':60,'revision':1})

    def test_new_start_is_idempotent_and_job_config_frozen(self):
        key=self.key()
        first=self.act('wenxin_card','new',{'revision':1},key)
        again=self.act('wenxin_card','new',{'revision':1},key)
        self.assertEqual(first,again)
        self.assertEqual(len(self.system.starts),1)
        self.assertEqual(len(self.current('wenxin_card')['history']),2)
        self.act('wenxin_card','settings',{'questions':['之后的问题'],'rounds':1,'interval':60,'revision':1})
        self.assertEqual(self.current('wenxin_card')['current']['config']['questions'],['问题一','问题二'])
        with self.assertRaises(Conflict):self.act('wenxin_card','new',{'revision':2})

    def test_pause_does_not_stop_process_and_resume_waits_for_drain(self):
        self.act('baidu_ai','new',{'revision':1})
        current=self.current('baidu_ai')['current']
        service=self.system.starts[-1]
        self.act('baidu_ai','pause')
        self.assertEqual(self.current('baidu_ai')['current']['state'],'pausing')
        with self.assertRaises(Conflict):self.act('baidu_ai','resume')
        self.system.states[service]='inactive'
        self.assertEqual(self.current('baidu_ai')['current']['state'],'paused')
        self.act('baidu_ai','resume')
        self.assertEqual(len(self.system.starts),2)
        self.assertFalse((self.root/'batches'/current['batch']/'pause.json').exists())

    def test_stop_is_terminal_and_history_kept(self):
        self.act('wenxin_card','new',{'revision':1})
        self.act('wenxin_card','stop')
        self.system.states[self.system.starts[-1]]='inactive'
        self.assertEqual(self.current('wenxin_card')['current']['state'],'stopped')
        with self.assertRaises(Conflict):self.act('wenxin_card','resume')
        self.assertEqual(len(self.current('wenxin_card')['history']),2)

    def test_new_task_keeps_old_pending_batch_paused_across_boot(self):
        first=self.act('baidu_ai','new',{'revision':1})
        self.system.states[self.system.starts[-1]]='inactive'
        self.act('baidu_ai','new',{'revision':1})
        self.assertTrue((self.root/'batches'/first['batch']/'pause.json').exists())
        with self.control.connect() as db:
            self.assertEqual(db.execute('select stop_requested from jobs where batch=?',(first['batch'],)).fetchone()[0],1)

    def test_uncertain_start_does_not_duplicate_new_job(self):
        self.system.fail=True
        key=self.key()
        first=self.act('baidu_ai','new',{'revision':1},key)
        self.assertFalse(first['ok'])
        self.assertEqual(self.act('baidu_ai','new',{'revision':1},key),first)
        self.assertEqual(len(self.system.starts),1)
        self.assertEqual(len(self.current('baidu_ai')['history']),2)

    def test_unknown_capture_cannot_resume_or_create_replacement(self):
        self.act('baidu_ai','new',{'revision':1})
        state=self.current('baidu_ai')['current']
        self.system.states[self.system.starts[-1]]='inactive'
        path=self.root/'batches'/state['batch']/'collector/tasks.sqlite'
        with closing(sqlite3.connect(path)) as db:
            db.execute('create table captures(state text)')
            db.execute("insert into captures values('capturing')")
            db.commit()
        with self.assertRaises(Conflict):self.act('baidu_ai','resume')
        with self.assertRaises(Conflict):self.act('baidu_ai','new',{'revision':1})

    def test_deepseek_requires_fresh_login_and_search_has_no_login_action(self):
        with self.assertRaises(Conflict):self.act('deepseek','new',{'revision':1})
        with self.assertRaises(ValueError):self.act('wenxin_card','login')
        with self.assertRaises(ValueError):self.act('baidu_ai','login')

    def test_validation_and_reused_action_key_reject_different_input(self):
        for value in ({'questions':['x','x'],'rounds':1,'interval':60},
                      {'questions':['x'],'rounds':True,'interval':60},
                      {'questions':['x'],'rounds':1,'interval':1},
                      {'questions':['x\ny'],'rounds':1,'interval':60}):
            with self.assertRaises(ValueError):validate('baidu_ai',value)
        key=self.key()
        self.act('baidu_ai','settings',{'questions':['x'],'rounds':1,'interval':60,'revision':1},key)
        with self.assertRaises(Conflict):self.act('baidu_ai','new',{'revision':2},key)

    def test_native_new_job_uses_separate_batch_and_shared_tested_device(self):
        self.act('doubao1','settings',{'questions':['自定义甲','自定义乙','自定义丙'],'rounds':2,'interval':35,'revision':1})
        result=self.act('doubao1','new',{'revision':2})
        state=self.current('doubao1')['current']
        self.assertEqual(state['planned'],6)
        self.assertTrue(self.system.starts[-1].startswith('geo-native@'))
        self.assertTrue((self.root/'native/batches'/result['batch']).exists())
        self.assertEqual(read(self.root/'panel/jobs'/(result['batch']+'.json'))['rounds'],2)

    def test_http_controls_require_same_origin_csrf_and_deduplicate_start(self):
        import fleet_status
        with patch.object(fleet_status,'CONTROLLER',self.control):
            server=ThreadingHTTPServer(('127.0.0.1',0),fleet_status.Handler)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                base='http://127.0.0.1:'+str(server.server_port)
                session=requests.Session();session.trust_env=False
                state=session.get(base+'/api/panel',timeout=5).json()
                url=base+'/api/control/baidu_ai/new'
                self.assertEqual(session.post(url,json={'revision':1},timeout=5).status_code,403)
                headers={'Origin':base,'X-CSRF-Token':state['csrf'],'X-Action-Id':self.key()}
                first=session.post(url,json={'revision':1},headers=headers,timeout=5)
                self.assertEqual(first.status_code,200,first.text)
                second=session.post(url,json={'revision':1},headers=headers,timeout=5)
                self.assertEqual(second.json(),first.json())
                self.assertEqual(len(self.system.starts),1)
                headers['Origin']='https://unrelated.example'
                self.assertEqual(session.post(url,json={'revision':1},headers=headers,timeout=5).status_code,403)
            finally:server.shutdown();server.server_close();thread.join(timeout=5)


if __name__=='__main__':unittest.main()

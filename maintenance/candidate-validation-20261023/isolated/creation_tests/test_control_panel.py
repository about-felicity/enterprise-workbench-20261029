
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[1]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
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

    def test_memory_snapshot_has_only_display_metrics(self):
        c=self.current('doubao2')['current'];path=self.root/'batches'/c['batch']/'bridge_health.json'
        h=read(path);h['memory']={'java_alloc_kib':204800,'java_limit_kib':524288,'pending':'java_fraction','raw_private_data':'not-for-display'};atomic(path,h)
        memory=self.current('doubao2')['current']['memory']
        self.assertEqual(memory['java_alloc_kib'],204800);self.assertEqual(memory['pending'],'java_fraction')
        self.assertNotIn('raw_private_data',memory)

    def test_delivery_diagnostics_are_actionable_and_redacted(self):
        c=self.current('wenxin_card')['current']
        atomic(self.root/'batches'/c['batch']/'bridge_health.json',{
            'status':'running_delivery_backoff','captured':3,'processed':2,'time':100,
            'errors':[{'code':'receiver_auth_required','retryable':False,'http_status':401,
                       'reason':'private-token','next_at':999}],
            'progress':{'phase':'delivery','pending_delivery':1,'secret':'private-token'}})
        snap=self.current('wenxin_card')['current']
        self.assertEqual(snap['pending_delivery'],1)
        self.assertEqual(snap['diagnostics'][0]['code'],'receiver_auth_required')
        self.assertNotIn('private-token',json.dumps(snap))

    def test_yuanbao_native_queue_is_independent_and_unknown_send_stays_blocked(self):
        original=self.current('doubao1')['current']
        result=self.act('yuanbao','new',{'revision':1})
        root=self.root/'redroid-yuanbao/batches'/result['batch']
        self.assertTrue(root.is_dir())
        self.assertEqual(self.current('doubao1')['current']['batch'],original['batch'])
        self.assertEqual(self.current('yuanbao')['current']['config']['interval'],45)
        with closing(sqlite3.connect(root/'tasks.sqlite')) as db:
            with db:
                db.execute('create table tasks(state text)')
                db.execute("insert into tasks values('prepared')")
        self.system.states[self.system.starts[-1]]='inactive'
        self.act('yuanbao','resume')
        with closing(sqlite3.connect(root/'tasks.sqlite')) as db:
            self.assertEqual(db.execute('select state from tasks').fetchone()[0],'prepared')
        with self.assertRaises(Conflict):self.act('yuanbao','new',{'revision':1})

    def test_new_native_jobs_are_question_only_and_allow_twelve_hour_capacity(self):
        self.act('doubao1','settings',{'questions':['推荐一款睫毛增长液'],'rounds':72,'interval':45,'revision':1})
        self.act('doubao1','new',{'revision':2})
        current=self.current('doubao1')['current']
        self.assertEqual(current['config']['prompt_mode'],'question_only')
        self.assertEqual(current['planned'],72)
        with self.assertRaises(ValueError):validate('doubao1',{'questions':['q'],'rounds':201,'interval':45})
        with self.assertRaises(ValueError):validate('deepseek',{'questions':['q'],'rounds':72,'interval':1200})

    def test_legacy_native_resume_cannot_send_old_marker_prompts(self):
        current=self.current('doubao1')['current']
        atomic(self.root/'batches'/current['batch']/'bridge_health.json',{'status':'stopped','captured':1,'planned':2})
        with self.assertRaisesRegex(Conflict,'附加任务提示'):self.act('doubao1','resume')

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
        self.act('baidu_ai','resume')
        with closing(sqlite3.connect(path)) as db:
            self.assertEqual(db.execute('select state from captures').fetchone()[0],'capturing')
        with self.assertRaises(Conflict):self.act('baidu_ai','new',{'revision':1})

    def test_deepseek_requires_fresh_login_and_search_has_no_login_action(self):
        with self.assertRaises(Conflict):self.act('deepseek','new',{'revision':1})
        with self.assertRaises(ValueError):self.act('wenxin_card','login')
        with self.assertRaises(ValueError):self.act('baidu_ai','login')

    def set_deepseek_ready(self, **changes):
        import time
        current=self.current('deepseek')
        value={'status':'ready','checked_at':time.time(),'batch':current['current']['batch'],'revision':current['revision']}
        value.update(changes)
        with self.control.connect() as db:
            db.execute('insert or replace into logins values(?,?)',('deepseek',json.dumps(value)))

    def test_deepseek_gate_requires_fresh_matching_batch_and_settings(self):
        import time
        self.assertFalse(self.current('deepseek')['readiness']['can_start'])
        self.set_deepseek_ready()
        self.assertTrue(self.current('deepseek')['readiness']['can_start'])
        self.set_deepseek_ready(checked_at=time.time()-301)
        self.assertFalse(self.current('deepseek')['readiness']['can_start'])
        with self.assertRaises(Conflict):self.act('deepseek','new',{'revision':1})
        self.set_deepseek_ready(batch='another-batch')
        with self.assertRaises(Conflict):self.act('deepseek','new',{'revision':1})
        self.set_deepseek_ready()
        self.act('deepseek','settings',{'questions':['新的问题'],'rounds':3,'interval':750,'revision':1})
        self.assertFalse(self.current('deepseek')['readiness']['can_start'])
        with self.assertRaises(Conflict):self.act('deepseek','new',{'revision':2})

    def test_login_success_never_bypasses_unknown_result_or_starts_tasks(self):
        self.set_deepseek_ready()
        current=self.current('deepseek')['current']
        path=self.root/'batches'/current['batch']/'collector/tasks.sqlite'
        path.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(path)) as db:
            with db:
                db.execute('create table captures(state text)')
                db.execute("insert into captures values('capturing')")
        gate=self.current('deepseek')['readiness']
        self.assertFalse(gate['can_start'])
        self.assertFalse(gate['can_resume'])
        self.assertEqual(self.system.starts,[])

    def test_manual_login_ready_is_bound_to_flow_batch_and_revision(self):
        import time
        import manual_login
        current=self.current('deepseek')
        flow={'id':'test-flow','status':'ready','batch':current['current']['batch'],
              'revision':1,'updated_at':time.time(),'expires_at':time.time()+900}
        with patch.object(manual_login,'state',return_value=flow):
            self.assertTrue(self.current('deepseek')['readiness']['can_start'])
            self.assertEqual(self.system.starts,[])
        self.act('deepseek','settings',{'questions':['不同问题'],'rounds':3,'interval':750,'revision':1})
        with patch.object(manual_login,'state',return_value=flow):
            self.assertFalse(self.current('deepseek')['readiness']['can_start'])

    def test_login_recovery_replaces_old_waiting_state_in_task_and_daily(self):
        import time
        current=self.current('deepseek')['current']
        path=self.root/'batches'/current['batch']/'bridge_health.json'
        atomic(path,{'status':'waiting_login','captured':1,'processed':1,'time':time.time()-60})
        self.set_deepseek_ready()
        actual=self.current('deepseek')
        self.assertEqual(actual['current']['state'],'ready_to_resume')
        self.assertEqual(actual['daily']['status'],'ready_to_resume')
        self.assertTrue(actual['readiness']['can_resume'])
        self.assertEqual(self.system.starts,[])
        self.system.states['old-deepseek.service']='active'
        self.assertEqual(self.current('deepseek')['current']['state'],'starting')
        atomic(path,{'status':'waiting_login','time':time.time()+1})
        self.assertEqual(self.current('deepseek')['current']['state'],'waiting_login')

    def test_fresh_login_cannot_bypass_pending_delivery_on_backend(self):
        self.set_deepseek_ready()
        current=self.current('deepseek')['current']
        atomic(self.root/'batches'/current['batch']/'bridge_health.json',
               {'status':'stopped','captured':2,'processed':1})
        self.assertFalse(self.current('deepseek')['readiness']['can_start'])
        with self.assertRaisesRegex(Conflict,'回传'):
            self.act('deepseek','new',{'revision':1})
        with self.assertRaisesRegex(Conflict,'回传'):
            self.act('deepseek','resume')
        self.assertEqual(self.system.starts,[])

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

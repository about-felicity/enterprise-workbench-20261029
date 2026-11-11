from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time
import unittest
from unittest.mock import patch
from datetime import datetime,timedelta
from daily_tasks import DailyTasks,today,installed,valid_day
from control_panel import atomic,read,Conflict
import test_control_panel as fixtures

class DailyTaskTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ControlTests();self.fixture.setUp()
        self.c=self.fixture.control;self.root=self.fixture.root
        self.counts={};self.c.daily_counts=lambda day:self.counts
        self.tasks=DailyTasks(self.c)
        self.day=today()
    def tearDown(self):self.fixture.tearDown()
    def model(self,model='baidu_ai'):return self.fixture.current(model)
    def apply(self,model='baidu_ai',questions=None,rounds=5):
        m=self.model(model)
        return self.fixture.act(model,'settings',{'questions':questions or ['问题一','问题二'],'rounds':rounds,
               'interval':600 if model=='deepseek' else 60,'revision':m['revision'],'apply_now':True,'day':self.day})
    def action(self,action,model='baidu_ai'):
        return self.fixture.act(model,action,{'scope':'daily','day':self.day})
    def finish(self,model,count):
        job=self.model(model)['current']
        atomic(self.root/'batches'/job['batch']/'bridge_health.json',{'status':'complete','captured':count,'processed':count,'geo_processed':count,'batch':job['batch']})
        with self.c.connect() as db:service=self.c.current(db,model)['service']
        self.fixture.system.states[service]='inactive'
    def test_apply_is_durable_without_mutating_current_batch_or_starting_mid_answer(self):
        old=self.model()['current'];self.fixture.system.states['old-baidu_ai.service']='active'
        self.apply(rounds=7)
        m=self.model()
        self.assertEqual(m['current']['config'],old['config'])
        self.assertEqual(m['daily']['config']['rounds'],7)
        self.assertTrue((self.root/'batches'/old['batch']/'pause.json').exists())
        self.tasks.reconcile();self.assertEqual(self.fixture.system.starts,[])
    def test_remaining_groups_never_resend_completed_questions(self):
        self.counts={'baidu_ai':{'问题一':3,'问题二':2}}
        self.apply();self.tasks.reconcile()
        m=self.model();self.assertEqual(m['current']['config']['questions'],['问题二'])
        self.assertEqual(m['current']['config']['rounds'],3)
        self.finish('baidu_ai',3);self.counts['baidu_ai']['问题二']=5
        self.tasks.reconcile();m=self.model()
        self.assertEqual(m['current']['config']['questions'],['问题一'])
        self.assertEqual(m['current']['config']['rounds'],2)
        self.finish('baidu_ai',2);self.counts['baidu_ai']['问题一']=5
        self.tasks.reconcile();self.assertEqual(self.model()['daily']['status'],'complete')
        self.assertEqual(len(self.fixture.system.starts),2)
    def test_lower_target_keeps_all_data_and_starts_nothing(self):
        self.counts={'baidu_ai':{'问题一':8,'问题二':8}}
        self.apply(rounds=3);self.tasks.reconcile()
        d=self.model()['daily'];self.assertEqual((d['completed'],d['target'],d['remaining']),(16,6,0))
        self.assertEqual(self.fixture.system.starts,[])
    def test_drained_doubao_segment_leaves_original_and_runs_only_independent_questions(self):
        from daily_dispatch import DailyController
        model='doubao4'
        self.c=DailyController(self.root,self.fixture.system,self.root/'native')
        self.fixture.control=self.c
        self.c.daily_counts=lambda day:self.counts
        self.tasks=DailyTasks(self.c)
        self.apply(model=model);self.tasks.reconcile()
        with self.c.connect() as db:original=self.c.current(db,model)
        root=self.c.batch_root(original)
        with closing(sqlite3.connect(root/'tasks.sqlite')) as db,db:
            db.execute('create table tasks(task_id text,question text,state text,request_id text,capture_retries int,prepared_at real)')
            db.execute("insert into tasks values('task','问题一','needs_attention','request',0,1)")
        atomic(root/'deferred_originals.json',{'task':'request'})
        atomic(root/'task-attempt-0.binding.json',{'request_id':'request'})
        health={'status':'needs_attention','tasks':{'needs_attention':1},'captured':1,'geo_processed':0,'next_readback_at':time.time()+300}
        atomic(root/'bridge_health.json',health)
        self.fixture.system.states[original['service']]='inactive'
        self.tasks.reconcile()
        self.assertEqual(self.model(model)['current']['batch'],original['batch'])
        atomic(root/'bridge_health.json',{**health,'geo_processed':1})
        atomic(self.c.marker(original),{'source':'control_panel','action':'pause'})
        self.assertEqual(self.c.deferable_segment(original,self.day,self.c.snapshot(original)),[])
        atomic(self.c.marker(original),{'source':'daily_tasks','allow_original_readback':True})
        self.tasks.reconcile()
        current=self.model(model)['current']
        self.assertNotEqual(current['batch'],original['batch'])
        self.assertEqual(current['config']['questions'],['问题二'])
        with closing(sqlite3.connect(root/'tasks.sqlite')) as db:
            self.assertEqual(db.execute('select state,request_id from tasks').fetchone(),('needs_attention','request'))
        self.counts[model]={'问题二':5}
        with self.c.connect() as db:job=self.c.current(db,model)
        atomic(self.c.batch_root(job)/'bridge_health.json',{'status':'complete','captured':5,'geo_processed':5})
        self.fixture.system.states[job['service']]='inactive'
        DailyTasks(self.c).reconcile()
        self.assertEqual(self.model(model)['daily']['status'],'needs_attention')
        self.assertEqual(len(self.fixture.system.starts),2)
    def test_native_validation_stop_waits_before_retrying_original_batch(self):
        model='yuanbao'
        self.apply(model=model);self.tasks.reconcile()
        with self.c.connect() as db:job=self.c.current(db,model)
        health={'status':'needs_attention','tasks':{'needs_attention':1},'time':time.time(),
                'progress':{'phase':'native_validation_stopped'}}
        atomic(Path(job['health']),health)
        self.fixture.system.states[job['service']]='inactive'
        self.tasks.reconcile();self.tasks.reconcile()
        self.assertEqual(len(self.fixture.system.starts),1)
        self.assertEqual(self.model(model)['daily']['status'],'needs_attention')
        atomic(Path(job['health']),{**health,'time':time.time()-301})
        self.tasks.reconcile()
        self.assertEqual(len(self.fixture.system.starts),2)
        self.assertEqual(self.model(model)['current']['batch'],job['batch'])


    def test_drained_yuanbao_segment_preserves_uncertain_send_and_counts_nontext(self):
        from daily_dispatch import DailyController
        from daily_tasks import question_digest
        model='yuanbao'
        self.c=DailyController(self.root,self.fixture.system,self.root/'native')
        self.fixture.control=self.c
        self.c.daily_counts=lambda day:self.counts
        self.tasks=DailyTasks(self.c)
        self.apply(model,questions=['待核对','无正文','下一题'],rounds=1)
        self.tasks.reconcile()
        with self.c.connect() as db:original=self.c.current(db,model)
        root=self.c.batch_root(original)
        with closing(sqlite3.connect(root/'tasks.sqlite')) as db,db:
            db.execute('create table tasks(task_id text,question text,state text,request_id text,capture_retries int,prepared_at real)')
            db.execute("insert into tasks values('uncertain','待核对','needs_attention',null,0,1)")
            db.execute("insert into tasks values('nontext','无正文','completed_nontext','original',0,2)")
        atomic(root/'uncertain_send_quarantine.json',{
            'uncertain':{'prepared_at':1,'question_sha256':question_digest('待核对')},
        })
        atomic(Path(original['health']),{'status':'needs_attention','tasks':{'needs_attention':1},
                                         'next_readback_at':time.time()+300})
        self.fixture.system.states[original['service']]='inactive'
        self.tasks.reconcile()
        current=self.model(model)
        self.assertNotEqual(current['current']['batch'],original['batch'])
        self.assertEqual(current['current']['config']['questions'],['下一题'])
        self.assertEqual(current['daily']['unavailable'],1)
        self.assertEqual(self.c.deferred_segments(model,self.day),{original['batch']:[question_digest('待核对')]})
        with closing(sqlite3.connect(root/'tasks.sqlite')) as db:
            self.assertEqual(db.execute("select state,request_id from tasks where task_id='uncertain'").fetchone(),
                             ('needs_attention',None))


    def test_added_and_removed_questions_change_only_remaining_work(self):
        self.counts={'baidu_ai':{'问题一':5,'问题二':4}}
        self.apply(questions=['问题一','新问题']);self.tasks.reconcile()
        self.assertEqual(self.model()['current']['config']['questions'],['新问题'])
        self.assertEqual(self.model()['current']['config']['rounds'],5)
    def test_manual_pause_survives_save_and_supervisor_restarts(self):
        self.action('pause');self.apply(rounds=8)
        DailyTasks(self.c).reconcile()
        self.assertEqual(self.model()['daily']['status'],'paused')
        self.assertEqual(self.fixture.system.starts,[])
        self.action('resume');DailyTasks(self.c).reconcile()
        self.assertEqual(len(self.fixture.system.starts),1)
        self.assertEqual(self.model()['current']['config']['rounds'],8)
    def test_resume_of_same_revision_reuses_original_segment(self):
        self.apply();self.tasks.reconcile();batch=self.model()['current']['batch']
        self.action('pause')
        self.finish('baidu_ai',1)
        atomic(self.root/'batches'/batch/'bridge_health.json',{'status':'paused','captured':0,'processed':0})
        self.tasks.reconcile();self.action('resume');self.tasks.reconcile()
        self.assertEqual(self.model()['current']['batch'],batch)
        self.assertEqual(len(self.fixture.system.starts),2)
    def test_lost_start_reply_adopts_original_registered_batch(self):
        self.apply();original=self.c.action
        def lost(*args,**kw):original(*args,**kw);raise OSError('lost reply')
        with patch.object(self.c,'action',side_effect=lost):self.tasks.reconcile()
        batch=self.model()['current']['batch'];self.assertEqual(len(self.fixture.system.starts),1)
        self.tasks.reconcile()
        self.assertEqual(self.model()['current']['batch'],batch)
        self.assertEqual(self.model()['daily']['batch'],batch)
        self.assertEqual(len(self.fixture.system.starts),1)
    def test_transient_controller_error_clears_after_successful_reconcile(self):
        self.apply()
        with patch.object(self.tasks,'_one',side_effect=OSError('temporary start failure')):self.tasks.reconcile()
        self.assertEqual(self.model()['daily']['error'],'后台正在重试：OSError')
        self.tasks.reconcile()
        self.assertIsNone(self.model()['daily']['error'])
        self.assertEqual(len(self.fixture.system.starts),1)
    def test_controlled_error_is_not_cleared_by_an_unrelated_success(self):
        self.apply()
        with patch.object(self.tasks,'_one',side_effect=Conflict('请检查当前配置')):self.tasks.reconcile()
        with patch.object(self.tasks,'_one',return_value=None):self.tasks.reconcile()
        self.assertEqual(self.model()['daily']['error'],'请检查当前配置')
    def test_healthy_same_revision_worker_clears_old_login_and_delivery_warning(self):
        self.apply();self.tasks.reconcile();job=self.model()['current']
        atomic(self.root/'batches'/job['batch']/'bridge_health.json',{'status':'running','captured':1,'geo_processed':1,'time':time.time(),'heartbeat_expires_at':time.time()+150})
        with self.c.connect() as db:db.execute('update daily_tasks set status=?,error=? where model=?',('waiting_login','请等待所有结果回传并核对回执后再开始或继续','baidu_ai'))
        self.tasks.reconcile()
        self.assertEqual(self.model()['daily']['status'],'running');self.assertIsNone(self.model()['daily']['error'])
        with self.c.connect() as db:self.assertEqual(self.tasks.row(db,'baidu_ai',self.day)['status'],'running')
        self.assertEqual(len(self.fixture.system.starts),1)
    def test_active_worker_with_pending_receipt_does_not_clear_delivery_warning(self):
        self.apply();self.tasks.reconcile();job=self.model()['current']
        atomic(self.root/'batches'/job['batch']/'bridge_health.json',{'status':'running','captured':2,'geo_processed':1,'time':time.time(),'heartbeat_expires_at':time.time()+150})
        with self.c.connect() as db:db.execute('update daily_tasks set error=? where model=?',('请等待所有结果回传并核对回执后再开始或继续','baidu_ai'))
        self.tasks.reconcile();self.assertIsNotNone(self.model()['daily']['error'])
    def test_pending_launch_cannot_start_after_manual_pause(self):
        self.apply()
        with self.c.connect() as db:
            row=self.tasks.row(db,'baidu_ai',self.day)
            db.execute('insert into daily_launches values(?,?,?,?,?,?,?)',('a'*32,'baidu_ai',self.day,row['revision'],'old-baidu_ai',json.dumps({'questions':['问题一'],'rounds':5,'interval':60}),0))
            db.execute('update daily_tasks set batch=?',('launch:'+'a'*32,))
        self.action('pause');self.tasks.reconcile();self.assertEqual(self.fixture.system.starts,[])
    def test_wenxin_waits_for_every_baidu_question_after_configuration_change(self):
        self.counts={'baidu_ai':{'问题一':5,'问题二':4}}
        self.apply('baidu_ai');self.apply('wenxin_card',rounds=8)
        self.tasks.reconcile()
        self.assertEqual(self.model('wenxin_card')['daily']['status'],'waiting_for_baidu')
        self.counts['baidu_ai']['问题二']=5
        self.finish('baidu_ai',1);self.tasks.reconcile()
        self.assertEqual(self.model('wenxin_card')['current']['config']['rounds'],8)
    def test_pg_failure_cannot_create_or_restart_work(self):
        self.apply()
        self.tasks.counts=lambda day:(_ for _ in ()).throw(OSError('database unavailable'))
        with self.assertRaises(OSError):self.tasks.reconcile()
        self.assertEqual(self.fixture.system.starts,[])
    def test_historical_requests_are_rejected_without_changing_settings(self):
        yesterday=(datetime.now()-timedelta(days=1)).date().isoformat()
        old=self.model()['revision']
        with self.assertRaises(ValueError):self.fixture.act('baidu_ai','settings',{'questions':['q'],'rounds':5,'interval':60,'revision':old,'apply_now':True,'day':yesterday})
        self.assertEqual(self.model()['revision'],old)
        with self.assertRaises(ValueError):self.fixture.act('baidu_ai','pause',{'scope':'daily','day':yesterday})
    def test_history_plan_snapshot_does_not_change_with_tomorrows_defaults(self):
        self.apply(rounds=8)
        self.fixture.act('baidu_ai','settings',{'questions':['new default'],'rounds':3,'interval':60,'revision':self.model()['revision']})
        self.assertEqual(self.model()['daily']['config']['rounds'],8)
        tomorrow=(datetime.now()+timedelta(days=1)).date().isoformat()
        d=next(m for m in self.c.all(tomorrow)['models'] if m['id']=='baidu_ai')['daily']
        self.assertEqual(d['config']['rounds'],3);self.assertTrue(d['editable'])
    def test_counts_and_schedule_are_independent_of_other_models(self):
        self.counts={'doubao1':{'问题一':2},'doubao2':{'问题一':7}}
        data=self.c.all();one=next(m for m in data['models'] if m['id']=='doubao1')['daily']
        two=next(m for m in data['models'] if m['id']=='doubao2')['daily']
        self.assertEqual(one['questions'][0]['completed'],2)
        self.assertEqual(two['questions'][0]['completed'],7)
    def test_repeated_daily_timer_cannot_override_manual_pause_or_saved_config(self):
        with self.c.connect() as db:self.tasks.ensure_scheduled(db,'baidu_ai',self.day)
        self.action('pause');self.apply(rounds=8)
        with self.c.connect() as db:self.tasks.ensure_scheduled(db,'baidu_ai',self.day)
        self.assertEqual(self.model()['daily']['desired'],'paused')
        self.assertEqual(self.model()['daily']['config']['rounds'],8)

    def test_old_deepseek_row_never_probes_or_blocks_other_channels(self):
        with self.c.connect() as db:
            cfg=self.tasks.config(db,'deepseek',self.day)
            db.execute('insert into daily_tasks values(?,?,?,?,?,?,?,?,?)',
                       ('deepseek',self.day,json.dumps(cfg),1,'running','waiting_login',None,time.time(),None))
            self.tasks.ensure_scheduled(db,'deepseek2',self.day)
            self.assertIsNone(self.tasks.row(db,'deepseek2',self.day))
        self.apply()
        with patch.object(self.c,'_login') as probe:
            self.tasks.reconcile();probe.assert_not_called()
        self.assertEqual(len(self.fixture.system.starts),1)
        status=read(self.root/'daily'/self.day/'status.json')
        self.assertEqual({row['model'] for row in status['models']},{'baidu_ai'})

    def test_save_replaces_uncommitted_old_launch_instead_of_starting_old_settings(self):
        self.apply()
        with self.c.connect() as db:
            row=self.tasks.row(db,'baidu_ai',self.day)
            db.execute('insert into daily_launches values(?,?,?,?,?,?,?)',('a'*32,'baidu_ai',self.day,row['revision'],'old-baidu_ai',json.dumps({'questions':['问题一'],'rounds':5,'interval':60}),0))
            db.execute('update daily_tasks set batch=?',('launch:'+'a'*32,))
        self.apply(rounds=8);self.tasks.reconcile()
        self.assertEqual(self.model()['current']['config']['rounds'],8)
        self.assertEqual(len(self.fixture.system.starts),1)
    def test_previous_day_is_not_reported_as_running_after_its_day_ends(self):
        self.apply(rounds=8)
        tomorrow=(datetime.now()+timedelta(days=1)).date().isoformat()
        with patch('daily_tasks.today',return_value=tomorrow):
            d=next(m for m in self.c.all(self.day)['models'] if m['id']=='baidu_ai')['daily']
        self.assertEqual(d['status'],'incomplete')
        self.assertFalse(d['editable'])
    def test_adopting_existing_day_preserves_full_plan_without_starting_any_work(self):
        with self.c.connect() as db:
            for model in fixtures.MODELS:self.tasks.ensure_scheduled(db,model,self.day,'observing')
        self.tasks.reconcile()
        self.assertEqual(self.fixture.system.starts,[])
        self.assertEqual(self.model()['daily']['config']['questions'],['问题一','问题二'])
        self.fixture.act('baidu_ai','settings',{'questions':['future'],'rounds':3,'interval':60,'revision':1})
        self.assertEqual(self.model()['daily']['config']['questions'],['问题一','问题二'])
    def test_future_save_and_pause_never_drain_todays_active_collector(self):
        tomorrow=(datetime.now()+timedelta(days=1)).date().isoformat()
        self.fixture.system.states['old-baidu_ai.service']='active'
        self.fixture.act('baidu_ai','settings',{'questions':['问题一'],'rounds':8,'interval':60,
                        'revision':1,'apply_now':True,'day':tomorrow})
        self.fixture.act('baidu_ai','pause',{'scope':'daily','day':tomorrow})
        self.tasks.reconcile()
        self.assertFalse((self.root/'batches/old-baidu_ai/pause.json').exists())
        self.assertEqual(self.fixture.system.starts,[])
        future=next(m for m in self.c.all(tomorrow)['models'] if m['id']=='baidu_ai')['daily']
        self.assertEqual(future['status'],'paused');self.assertEqual(future['config']['rounds'],8)
    def test_today_continuation_survives_editing_future_default_revision(self):
        self.apply(rounds=5)
        self.fixture.act('baidu_ai','settings',{'questions':['future'],'rounds':3,'interval':60,'revision':2})
        self.tasks.reconcile()
        self.assertEqual(self.model()['current']['config']['rounds'],5)
        self.assertEqual(self.model()['current']['config']['questions'],['问题一','问题二'])
    def test_save_at_launch_boundary_cannot_start_an_obsolete_configuration(self):
        self.apply(rounds=5);original=self.c.action
        other=fixtures.Controller(self.root,self.fixture.system,self.root/'native')
        def race(*args,**kwargs):
            other.action('baidu_ai','settings',{'questions':['问题一'],'rounds':8,'interval':60,
                         'revision':2,'apply_now':True,'day':self.day},self.fixture.key())
            return original(*args,**kwargs)
        with patch.object(self.c,'action',side_effect=race):self.tasks.reconcile()
        self.assertEqual(self.fixture.system.starts,[])
        self.tasks.reconcile()
        self.assertEqual(self.model()['current']['config']['rounds'],8)
        self.assertEqual(len(self.fixture.system.starts),1)
    def test_pause_at_launch_boundary_prevents_the_pending_segment(self):
        self.apply();original=self.c.action
        other=fixtures.Controller(self.root,self.fixture.system,self.root/'native')
        def race(*args,**kwargs):
            other.action('baidu_ai','pause',{'scope':'daily','day':self.day},self.fixture.key())
            return original(*args,**kwargs)
        with patch.object(self.c,'action',side_effect=race):self.tasks.reconcile()
        self.tasks.reconcile();self.assertEqual(self.fixture.system.starts,[])
    def test_pause_after_registration_blocks_sending_before_process_start(self):
        self.apply();original=self.fixture.system.start
        other=fixtures.Controller(self.root,self.fixture.system,self.root/'native')
        def before_start(service):
            other.action('baidu_ai','pause',{'scope':'daily','day':self.day},self.fixture.key())
            original(service)
        with patch.object(self.fixture.system,'start',side_effect=before_start):self.tasks.reconcile()
        with self.c.connect() as db:job=self.c.current(db,'baidu_ai')
        self.assertTrue(self.c.marker(job).exists())
        self.assertEqual(self.model()['daily']['desired'],'paused')

if __name__=='__main__':unittest.main()

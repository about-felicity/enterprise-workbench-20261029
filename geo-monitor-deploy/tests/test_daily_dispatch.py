from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import time
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

from control_panel import atomic,Conflict
from daily_dispatch import due,main,DailyController,operation_id
import test_control_panel as control_tests


class DailyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=control_tests.ControlTests();self.fixture.setUp()
        self.root=self.fixture.root;self.control=self.fixture.control
        self.plan={'enabled':True,'start_date':'2026-10-17','time':'05:00','timezone':'Asia/Shanghai',
                   'models':['wenxin_card','baidu_ai','yuanbao']}
        atomic(self.root/'daily_plan.json',self.plan)
        self.now=datetime(2026,10,17,5,0,tzinfo=ZoneInfo('Asia/Shanghai'))
    def tearDown(self):self.fixture.tearDown()

    def test_clock_timezone_start_date_and_daily_creation_is_idempotent(self):
        self.assertFalse(due(self.plan,self.now.replace(hour=4,minute=59)))
        self.assertFalse(due(self.plan,self.now.replace(day=16)))
        self.assertTrue(due(self.plan,self.now))
        first=main(self.root,now=self.now,control=self.control)
        self.assertEqual(len(self.fixture.system.starts),2)
        again=main(self.root,now=self.now,control=self.control)
        self.assertEqual(len(self.fixture.system.starts),2)
        self.assertEqual([r.get('batch') for r in first['models']],[r.get('batch') for r in again['models']])
        self.assertEqual(next(r for r in first['models'] if r['model']=='wenxin_card')['state'],'waiting_for_baidu')
        self.assertNotEqual(operation_id('2026-10-17','baidu_ai'),operation_id('2026-10-18','baidu_ai'))

    def test_wenxin_waits_for_all_baidu_results_and_processed_receipts(self):
        from daily_dispatch import dispatch_one
        from unittest.mock import Mock
        control=Mock()
        baidu={'batch':'b','state':'complete','planned':105,'captured':105,'processed':104,
               'pending_delivery':1,'needs_review':0}
        wenxin={'batch':'old','service_state':'inactive'}
        control.all.return_value={'models':[{'id':'baidu_ai','current':baidu},
                                            {'id':'wenxin_card','current':wenxin,'revision':1}]}
        day='2026-10-17';atomic(self.root/'daily'/day/'baidu_ai.json',{'batch':'b'})
        self.assertEqual(dispatch_one(control,self.root,day,'wenxin_card')['state'],'waiting_for_baidu')
        control.action.assert_not_called()
        baidu.update(processed=105,pending_delivery=0,state='complete_with_unavailable')
        self.assertEqual(dispatch_one(control,self.root,day,'wenxin_card')['state'],'waiting_for_baidu')
        baidu['state']='complete'
        control.connect=self.control.connect
        control.action.return_value={'batch':'new-wenxin','ok':True}
        self.assertEqual(dispatch_one(control,self.root,day,'wenxin_card')['state'],'running')
        control.action.assert_called_once()

    def test_login_failure_does_not_block_other_models_or_repeat_probes(self):
        atomic(self.root/'daily_plan.json',{**self.plan,'models':['deepseek','baidu_ai']})
        with self.control.connect() as db:
            db.execute('insert or replace into logins values(?,?)',('deepseek',json.dumps({'status':'login_required','checked_at':0})))
        with patch.object(self.control,'_login') as probe:
            first=main(self.root,now=self.now,control=self.control)
            self.assertEqual(first['models'][0]['state'],'waiting_login')
            self.assertEqual(first['models'][1]['state'],'running')
            main(self.root,now=self.now,control=self.control)
            self.assertEqual(probe.call_count,1)

    def test_prior_day_rollover_archives_unknown_rows_without_reset_or_resend(self):
        model='baidu_ai';old=self.fixture.current(model)['current'];batch=old['batch']
        dbpath=self.root/'batches'/batch/'collector/tasks.sqlite'
        dbpath.parent.mkdir(parents=True,exist_ok=True)
        with closing(sqlite3.connect(dbpath)) as db:
            db.execute('create table captures(state text)');db.execute("insert into captures values('needs_attention')");db.commit()
        with self.assertRaises(Conflict):self.fixture.act(model,'new',{'revision':1})
        with self.control.connect() as db:db.execute('update jobs set created=? where batch=?',(time.time()-86400,batch))
        daily=DailyController(self.root,self.fixture.system,self.root/'native')
        daily.rollover_batch=batch
        result=daily.action(model,'new',{'revision':1},operation_id('test-day',model))
        self.assertTrue(result['ok'])
        with closing(sqlite3.connect(dbpath)) as db:self.assertEqual(db.execute('select state from captures').fetchone()[0],'needs_attention')
        self.assertTrue(list((self.root/'daily').glob('*/prior-day-archives/*/tasks.sqlite')))


if __name__=='__main__':unittest.main()

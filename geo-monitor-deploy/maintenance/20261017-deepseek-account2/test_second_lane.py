import importlib.util
import json
from pathlib import Path
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tests'))
import test_control_panel as fixtures
from control_panel import DEEPSEEK_CHANNELS, Conflict, validate
from daily_tasks import DEVICES, DailyTasks, today, database_counts, _cache
from capture_bridge import envelope, verify_receipt


class SecondLaneTests(unittest.TestCase):
    def setUp(self):
        self.fixture=fixtures.ControlTests();self.fixture.setUp()
        self.control=self.fixture.control
    def tearDown(self):self.fixture.tearDown()
    def ready(self):
        with self.control.connect() as db:
            job=self.control.current(db,'deepseek2')
            db.execute('insert or replace into logins values(?,?)',('deepseek2',json.dumps({'status':'ready','checked_at':time.time(),'batch':job['batch'],'revision':1})))
    def test_new_task_is_routed_to_second_device_and_separate_root(self):
        with self.assertRaises(Conflict):self.fixture.act('deepseek2','new',{'revision':1})
        self.ready();result=self.fixture.act('deepseek2','new',{'revision':1})
        with self.control.connect() as db:job=self.control.current(db,'deepseek2')
        config=json.loads(job['config'])
        self.assertEqual(config['device'],'deepseek-hpe14-account2')
        self.assertIn('redroid-deepseek-account2',job['health'])
        self.assertEqual(config['prompt_mode'],'question_only')
        self.assertNotEqual(self.fixture.current('deepseek')['current']['batch'],result['batch'])
    def test_primary_and_secondary_ingest_counts_are_separate(self):
        _cache.clear()
        raw=[{'source_device':'deepseek-hpe14-android13','question':'同一问题','n':14},
             {'source_device':'deepseek-hpe14-account2','question':'同一问题','n':1}]
        with patch('daily_tasks.subprocess.check_output',return_value=json.dumps(raw)):
            counts=database_counts(today())
        self.assertEqual(counts['deepseek']['同一问题'],14)
        self.assertEqual(counts['deepseek2']['同一问题'],1)
    def test_second_channel_can_pause_without_affecting_first(self):
        self.fixture.act('deepseek2','pause',{'scope':'daily','day':today()})
        with self.control.connect() as db:
            self.assertEqual(DailyTasks(self.control).row(db,'deepseek2',today())['desired'],'paused')
            self.assertIsNone(DailyTasks(self.control).row(db,'deepseek',today()))
    def test_receiver_identity_remains_deepseek_but_device_is_second(self):
        result={'question':'问题','body':'完整正文','body_capture_complete':True,'source_capture_complete':True,
                'sources':[{'title':'来源','url':'https://example.com/'}],'capture_mode':'android_app_wcdb_question_only',
                'captured_at':'2026-10-17T06:00:00+00:00'}
        row={'ordinal':0,'round':1,'task_id':'second-task','batch':'second-batch','finished':123}
        config={'model':'deepseek2','device':'deepseek-hpe14-account2','rounds':3}
        value=envelope(row,result,config)
        self.assertEqual(value['model'],'deepseek')
        self.assertEqual(value['source_device'],'deepseek-hpe14-account2')
        self.assertEqual(value['record']['capture_task_id'],'second-task')


if __name__=='__main__':unittest.main()

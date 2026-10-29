from datetime import datetime
import json,unittest,uuid
from zoneinfo import ZoneInfo
import test_control_panel as fixtures
from control_panel import atomic,read,Conflict
from daily_dispatch import due
from schedule_control import save,view,validate

class ScheduleTests(unittest.TestCase):
 def setUp(self):
  self.fixture=fixtures.ControlTests();self.fixture.setUp();self.c=self.fixture.control;self.calls=[]
  self.fixture.system.configure_daily_schedule=lambda start,enabled:self.calls.append((start,enabled))
  atomic(self.c.base/'daily_plan.json',{'enabled':True,'time':'05:00','timezone':'Asia/Shanghai','start_date':'2026-10-17','models':['baidu_ai','wenxin_card'],'card_order':'baidu_complete_then_wenxin'})
 def tearDown(self):self.fixture.tearDown()
 def test_save_changes_timer_and_plan_without_stopping_or_starting_collectors(self):
  with self.c.connect() as db:before=[tuple(r) for r in db.execute('select * from settings')]
  value={'enabled':True,'time':'06:35','revision':0};key=uuid.uuid4().hex
  result=save(self.c,value,key);self.assertTrue(result['ok']);self.assertEqual(self.calls,[('06:35',True)])
  self.assertEqual(read(self.c.base/'daily_plan.json')['card_order'],'baidu_complete_then_wenxin')
  self.assertEqual(save(self.c,value,key),result);self.assertEqual(len(self.calls),1)
  self.assertEqual(self.fixture.system.starts,[])
  with self.c.connect() as db:self.assertEqual([tuple(r) for r in db.execute('select * from settings')],before)
  with self.assertRaises(Conflict):save(self.c,{'enabled':False,'time':'07:00','revision':0},uuid.uuid4().hex)
 def test_disabled_schedule_and_next_time(self):
  save(self.c,{'enabled':False,'time':'07:10','revision':0},uuid.uuid4().hex)
  self.assertIsNone(view(self.c.base)['next_run']);self.assertEqual(self.calls,[('07:10',False)])
 def test_configured_hour_and_minute_are_enforced(self):
  plan=read(self.c.base/'daily_plan.json');plan['time']='06:35'
  now=datetime(2026,10,17,6,34,tzinfo=ZoneInfo('Asia/Shanghai'))
  self.assertFalse(due(plan,now));self.assertTrue(due(plan,now.replace(minute=35)))
  self.assertFalse(due({**plan,'enabled':False},now.replace(hour=7)))
 def test_next_run_uses_beijing_and_start_date(self):
  now=datetime(2026,10,16,16,0,tzinfo=ZoneInfo('Asia/Shanghai'))
  self.assertEqual(view(self.c.base,now)['next_run'],'2026-10-17T05:00:00+08:00')
 def test_invalid_input_cannot_become_systemd_command(self):
  for v in [{'enabled':'yes','time':'05:00','revision':0},{'enabled':True,'time':'25:00','revision':0},{'enabled':True,'time':'05:00\nOnBootSec=1','revision':0}]:
   with self.assertRaises(ValueError):validate(v)
  self.assertEqual(self.calls,[])
 def test_timer_failure_rolls_back_plan(self):
  original=read(self.c.base/'daily_plan.json')
  def fail(start,enabled):raise OSError('fixture')
  self.fixture.system.configure_daily_schedule=fail
  with self.assertRaises(RuntimeError):save(self.c,{'enabled':True,'time':'06:35','revision':0},uuid.uuid4().hex)
  self.assertEqual(read(self.c.base/'daily_plan.json'),original)
 def test_future_preconfigured_task_cannot_start_early_or_when_schedule_disabled(self):
  from daily_tasks import DailyTasks,today
  tasks=DailyTasks(self.c)
  with self.c.connect() as db:
   tasks.ensure_scheduled(db,'doubao1',today())
   db.execute("update daily_tasks set status='scheduled' where model='doubao1'")
  atomic(self.c.base/'daily_plan.json',{**read(self.c.base/'daily_plan.json'),'enabled':False})
  tasks._one('doubao1',today(),{})
  self.assertEqual(self.fixture.system.starts,[])
  with self.c.connect() as db:self.assertEqual(tasks.row(db,'doubao1',today())['status'],'scheduled')

if __name__=='__main__':unittest.main()

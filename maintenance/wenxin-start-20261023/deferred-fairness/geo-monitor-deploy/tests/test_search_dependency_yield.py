import json,sqlite3,time,unittest
from pathlib import Path
from unittest.mock import patch
import test_daily_tasks as helpers
from control_panel import atomic,read

class DependencyYieldTests(unittest.TestCase):
 def setUp(self):
  self.h=helpers.DailyTaskTests();self.h.setUp();self.c=self.h.c;self.tasks=self.h.tasks
  self.h.apply('baidu_ai');self.h.apply('wenxin_card',rounds=8);self.tasks.reconcile()
  with self.c.connect() as db:
   job=self.c.current(db,'baidu_ai');db.execute('update jobs set created=? where batch=?',(time.time()-700,job['batch']))
  self.job=job;self.root=Path(job['health']).parent
  atomic(Path(job['health']),{'status':'running','time':time.time(),'captured':0,'processed':0,'errors':[]})
  atomic(self.root/'collector/search_recovery.json',{'kind':'read_error','blocked':0})
  path=self.root/'collector/tasks.sqlite';path.parent.mkdir(parents=True,exist_ok=True)
  with sqlite3.connect(path) as db:
   db.executescript('create table captures(task_id text,batch text,question text);create table search_recovery_attempts(id integer primary key,task_id text,previous_result text,epoch real);')
   db.execute('insert into captures values(?,?,?)',('t',job['batch'],'问题一'))
   v={'availability':'no_card','absence_evidence':{'url':'https://www.baidu.com/s?wd=问题一','query':'问题一','readyState':'complete','cardPresent':False,'searchResultsCount':10}}
   for i in range(6):db.execute('insert into search_recovery_attempts values(?,?,?,?)',(i+1,'t',json.dumps(v),time.time()-i))
 def tearDown(self):self.h.tearDown()
 def evidence(self):
  with self.c.connect() as db:return self.tasks.baidu_absence_yield(db,self.h.day)
 def test_confirmed_persistent_absence_starts_wenxin_without_completing_baidu(self):
  self.assertIsNotNone(self.evidence());before=self.h.model('baidu_ai')['current']['batch']
  self.tasks.reconcile();w=self.h.model('wenxin_card')
  self.assertEqual(w['daily']['status'],'running');self.assertEqual(w['current']['config']['rounds'],8)
  self.assertEqual(self.h.model('baidu_ai')['current']['batch'],before)
  self.assertEqual(self.h.model('baidu_ai')['daily']['completed'],0)
  self.assertTrue((self.c.base/'daily'/self.h.day/'wenxin_search_yield.json').is_file())
 def test_missing_evidence_verification_manual_pause_and_delivery_backlog_do_not_yield(self):
  atomic(self.root/'collector/search_recovery.json',{'kind':'verification','blocked':1});self.assertIsNone(self.evidence())
  atomic(self.root/'collector/search_recovery.json',{'kind':'read_error','blocked':0})
  atomic(self.c.marker(self.job),{'source':'user'});self.assertIsNone(self.evidence());self.c.marker(self.job).unlink()
  atomic(Path(self.job['health']),{'status':'running_delivery_backoff','time':time.time(),'errors':[]});self.assertIsNone(self.evidence())
  atomic(Path(self.job['health']),{'status':'running','time':time.time(),'errors':[]})
  with sqlite3.connect(self.root/'collector/tasks.sqlite') as db:db.execute('delete from search_recovery_attempts where id=1')
  self.assertIsNone(self.evidence())
 def test_stale_wrong_query_partial_card_and_old_day_fail_closed(self):
  path=self.root/'collector/tasks.sqlite'
  for change in ({'query':'别的问题'},{'cardPresent':True},{'readyState':'loading'}):
   with sqlite3.connect(path) as db:
    v=json.loads(db.execute('select previous_result from search_recovery_attempts where id=6').fetchone()[0]);original=json.dumps(v);v['absence_evidence'].update(change)
    db.execute('update search_recovery_attempts set previous_result=? where id=6',(json.dumps(v),))
   self.assertIsNone(self.evidence())
   with sqlite3.connect(path) as db:db.execute('update search_recovery_attempts set previous_result=? where id=6',(original,))
  with self.c.connect() as db:
   config=json.loads(self.job['config']);config['daily_date']='2000-01-01';db.execute('update jobs set config=? where batch=?',(json.dumps(config),self.job['batch']))
  self.assertIsNone(self.evidence())

if __name__=='__main__':unittest.main()

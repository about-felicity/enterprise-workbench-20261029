import json,os,subprocess,sys,tempfile,time,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from . import parallel,runtime,worker,studio,materials
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.deepseek_api import APIError

class ParallelTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.base=Path(self.tmp.name)
 def job(self,i,scope='p'):
  root=self.base/'runs'/('creation-1000-'+format(i,'08x'))
  atomic_json(root/'job.json',{'job_id':root.name,'date':'2026-10-26','preparation':'ready','studio_plan_id':scope})
  atomic_json(root/'control.json',{'paused':False,'revision':1});return root
 def test_capacity_fairness_drain_and_no_duplicate_launch(self):
  roots=[self.job(i,'a' if i<5 else 'b') for i in range(6)]
  handles=[]
  def launch(root):
   p=MagicMock(pid=len(handles)+100);p.poll.return_value=None;handles.append((root,p));return p
  s=parallel.Scheduler(self.base,2,launch);s.tick()
  self.assertEqual(len(handles),2);self.assertEqual({runtime.read(r/'job.json')['studio_plan_id'] for r,p in handles},{'a','b'})
  s.tick();self.assertEqual(len(handles),2)
  handles[0][1].poll.return_value=0;s.tick(draining=True);self.assertEqual(len(handles),2)
  s.tick();self.assertEqual(len(handles),3);self.assertEqual(len(s.active),2)
 def test_failed_child_pauses_only_its_job(self):
  root=self.job(1);p=MagicMock(pid=12);p.poll.return_value=None
  s=parallel.Scheduler(self.base,1,lambda r:p);s.tick();p.poll.return_value=1;s.tick()
  self.assertTrue(runtime.read(root/'control.json')['paused']);self.assertEqual(len(s.active),0)
 def test_busy_job_lock_does_not_pause_or_duplicate(self):
  root=self.job(1)
  with process_lock(root/'api/worker.lock'),patch.object(worker,'execute') as execute:
   with self.assertRaises(RuntimeError):worker.execute_once(root)
   execute.assert_not_called()
  self.assertFalse(runtime.read(root/'control.json')['paused'])
 def test_shared_cache_wait_reenters_original_without_paid_retry(self):
  root=self.job(1);error=RuntimeError('Another collector uses this runtime; do not share browser profiles concurrently');error.__cause__=BlockingIOError()
  atomic_json(root/'api/active.json',{'state':'REQUESTING','run_id':'same'})
  with patch.object(worker,'SharedBudget',return_value=MagicMock()),patch.object(worker,'CreationClient'),patch.object(worker,'Worker') as engine:
   engine.return_value.once.side_effect=error;worker.execute_once(root)
  self.assertFalse(runtime.read(root/'control.json')['paused']);self.assertFalse(parallel.eligible(root))
  self.assertEqual(runtime.read(root/'api/active.json')['run_id'],'same')
 def test_pause_terminal_and_backoff_are_not_scheduled(self):
  root=self.job(1);atomic_json(root/'control.json',{'paused':True});self.assertFalse(parallel.eligible(root))
  atomic_json(root/'control.json',{'paused':False});atomic_json(root/'days/2026-10-26/day.json',{'status':'complete'})
  self.assertFalse(parallel.eligible(root))
 def test_real_process_overlap_and_stage_handoff(self):
  roots=[self.job(i,str(i)) for i in range(4)]
  code="""import json,time,sys
from pathlib import Path
from creation import worker,runtime
from unittest.mock import MagicMock,patch
r=Path(sys.argv[1])
class Engine:
 def __init__(self,*a):pass
 def once(self,day):
  events=[]
  for stage in ('analysis','writer'):
   start=time.time();time.sleep(.35);events.append({'stage':stage,'start':start,'end':time.time()})
  runtime.atomic_json(r/'timing.json',events)
  runtime.atomic_json(r/'days'/day/'day.json',{'status':'complete'})
  return {'status':'complete'}
with patch.object(worker,'SharedBudget',return_value=MagicMock()),patch.object(worker,'CreationClient'),patch.object(worker,'Worker',Engine):worker.execute_once(r)
"""
  children=[]
  def launch(root):
   p=subprocess.Popen([sys.executable,'-c',code,str(root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE);children.append(p);return p
  s=parallel.Scheduler(self.base,4,launch);s.tick();self.assertEqual(len(s.active),4)
  deadline=time.time()+20
  while s.active and time.time()<deadline:s.tick();time.sleep(.02)
  self.assertFalse(s.active)
  for p in children:
   out,err=p.communicate();self.assertEqual(p.returncode,0,err.decode())
  times=[runtime.read(r/'timing.json') for r in roots]
  self.assertLess(max(t[0]['start'] for t in times),min(t[0]['end'] for t in times))
  self.assertTrue(all(t[1]['start']>=t[0]['end'] for t in times))
 def test_concurrent_budget_reservations_cannot_overspend_same_task(self):
  shared=self.base/'shared';atomic_json(shared/'settings.json',{'article_budget_cny':.1,'daily_budget_cny':.1})
  roots=[self.job(i,'one-plan') for i in range(8)]
  for r in roots:
   j=runtime.read(r/'job.json');j['budget_limits']={'article_budget_cny':.1,'task_budget_cny':.1};atomic_json(r/'job.json',j)
  with patch.object(runtime,'SHARED',shared):runtime.SharedBudget(roots[0]).db.close()
  code="""import sys,time
from pathlib import Path
from creation import runtime
from geo_source_cards.api_budget import BudgetExceeded
runtime.SHARED=Path(sys.argv[1]);root=Path(sys.argv[2]);b=runtime.SharedBudget(root)
while not Path(sys.argv[3]).exists():time.sleep(.01)
try:b.reserve({'messages':[{'role':'user','content':'fixture'}],'max_tokens':10000},root/'call',{'date':'2026-10-26','category':'rank','number':1},'writer');print('reserved')
except BudgetExceeded:print('rejected')
finally:b.db.close()
"""
  gate=self.base/'go';children=[subprocess.Popen([sys.executable,'-c',code,str(shared),str(r),str(gate)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for r in roots];gate.touch()
  results=[]
  for p in children:
   out,err=p.communicate(timeout=20);self.assertEqual(p.returncode,0,err.decode());results.append(out.decode().strip())
  self.assertEqual(results.count('reserved'),1);self.assertEqual(results.count('rejected'),7)

if __name__=='__main__':unittest.main()

import unittest
from datetime import datetime
from unittest.mock import patch
from .test_studio import StudioTests
from . import studio,runtime,materials

class TaskControlsTests(StudioTests):
 def job(self,pid,state='complete_with_failures',suffix='a'):
  day='2099-10-17';jid='creation-1234567890-'+suffix*8;root=runtime.BASE/'runs'/jid
  runtime.atomic_json(root/'job.json',{'job_id':jid,'date':day,'studio_plan_id':pid,'question':'问题'+suffix})
  runtime.atomic_json(root/'days'/day/'day.json',{'status':state})
  return root,{'job_id':jid,'date':day,'studio_plan_id':pid,'question':'问题'+suffix,'day':{'status':state},'articles':[]}

 def test_delete_is_durable_idempotent_and_keeps_history(self):
  p=studio.plan(self.plan()['plan_id']);pid=p['plan_id'];day='2099-10-17'
  studio.ensure_day(p,day);root,_=self.job(pid);(root/'article.md').write_text('保留正文')
  capture=studio.capture_root(pid)
  runtime.atomic_json(capture/'days'/day/'config.json',{'questions':p['questions']})
  first=runtime.action('plan_delete',{'plan_id':pid},'a'*32)
  self.assertEqual(first,runtime.action('plan_delete',{'plan_id':pid},'a'*32))
  self.assertTrue(studio.delete_plan({'plan_id':pid})['deleted'])
  self.assertEqual(studio.plans(),[]);self.assertEqual(studio.snapshot([])['daily_tasks'],[])
  self.assertTrue(runtime.read(capture/'settings.json')['paused']);self.assertFalse(runtime.read(capture/'settings.json')['enabled'])
  self.assertTrue(runtime.read(root/'control.json')['paused']);self.assertTrue(runtime.read(studio.day_path(pid,day))['paused'])
  self.assertEqual((root/'article.md').read_text(),'保留正文');self.assertTrue((capture/'days'/day/'config.json').exists())
  with patch.object(runtime,'action') as enqueue:
   studio.advance(p,day,datetime.now(studio.ZONE));enqueue.assert_not_called()
  with self.assertRaisesRegex(ValueError,'删除'):studio.save_plan(p)
  with patch.object(runtime,'balance') as balance:
   with self.assertRaisesRegex(ValueError,'删除'):runtime.resume(root)
   balance.assert_not_called()

 def test_terminal_daily_state_wins_over_stale_pause(self):
  p=studio.plan(self.plan()['plan_id']);pid=p['plan_id'];day='2099-10-17'
  task=studio.ensure_day(p,day);task['paused']=True;runtime.atomic_json(studio.day_path(pid,day),task)
  _,a=self.job(pid,suffix='a');_,b=self.job(pid,suffix='b')
  progress=[{'id':m,'name':m,'completed':2,'blocked':{}} for m in p['channels']]
  with patch.object(materials,'progress',return_value=progress):
   row=studio.snapshot([a,b])['daily_tasks'][0]
  self.assertEqual(row['status'],'complete_with_failures');self.assertEqual(row['allowed_actions'],[])
  with patch.object(runtime,'status',return_value={'studio':{'daily_tasks':[row]}}),patch.object(materials,'control') as control:
   for pause in (True,False):
    with self.assertRaisesRegex(ValueError,'结束'):studio.day_control({'plan_id':pid,'date':day},pause)
   control.assert_not_called()

 def test_partial_finished_job_does_not_hide_active_work(self):
  p=studio.plan(self.plan()['plan_id']);pid=p['plan_id'];studio.ensure_day(p,'2099-10-17')
  _,a=self.job(pid,suffix='a');_,b=self.job(pid,state='running',suffix='b')
  with patch.object(materials,'progress',return_value=[{'id':m,'completed':2,'blocked':{}} for m in p['channels']]):
   row=studio.snapshot([a,b])['daily_tasks'][0]
  self.assertEqual(row['status'],'creating');self.assertEqual(row['allowed_actions'],['day_pause'])

 def test_all_terminal_job_controls_rejected_before_balance(self):
  p=studio.plan(self.plan()['plan_id'])
  with patch.object(runtime,'balance') as balance:
   for state in studio.TERMINAL_JOBS:
    root,_=self.job(p['plan_id'],state)
    with self.assertRaisesRegex(ValueError,'结束'):runtime.assert_job_controllable(root)
    with self.assertRaisesRegex(ValueError,'结束'):runtime.resume(root)
   balance.assert_not_called()


 def test_terminal_task_with_extra_historical_jobs_is_still_ended(self):
  p=studio.plan(self.plan()['plan_id']);pid=p['plan_id'];studio.ensure_day(p,'2099-10-17')
  jobs=[self.job(pid,suffix=n)[1] for n in ('a','b','c')]
  with patch.object(materials,'progress',return_value=[{'id':m,'completed':2,'blocked':{}} for m in p['channels']]):
   row=studio.snapshot(jobs)['daily_tasks'][0]
  self.assertEqual(row['status'],'complete_with_failures');self.assertEqual(row['allowed_actions'],[])

if __name__=='__main__':unittest.main()

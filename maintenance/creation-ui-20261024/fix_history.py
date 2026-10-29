from pathlib import Path
R=Path(__file__).resolve().parents[2]/'geo-monitor-deploy/creation'
p=R/'studio.py';s=p.read_text('utf8').replace("ended=bool(js) and len(js)==", "ended=bool(js) and len(js)>=");p.write_bytes(s.encode('utf8'))
p=R/'test_task_controls.py';s=p.read_text('utf8');insert='''
 def test_terminal_task_with_extra_historical_jobs_is_still_ended(self):
  p=studio.plan(self.plan()['plan_id']);pid=p['plan_id'];studio.ensure_day(p,'2099-10-17')
  jobs=[self.job(pid,suffix=n)[1] for n in ('a','b','c')]
  with patch.object(materials,'progress',return_value=[{'id':m,'completed':2,'blocked':{}} for m in p['channels']]):
   row=studio.snapshot(jobs)['daily_tasks'][0]
  self.assertEqual(row['status'],'complete_with_failures');self.assertEqual(row['allowed_actions'],[])

''';s=s.replace("if __name__=='__main__':",insert+"if __name__=='__main__':");p.write_bytes(s.encode('utf8'))

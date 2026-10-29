from pathlib import Path
p=Path('maintenance/automatic-supplement-20261028/test_supplement.py');s=p.read_text('utf8');s=s.replace('unittest.main()', ''' def test_refresh_keeps_completed_and_inflight(self):
  t={'plan':{'plan_id':'plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','channels':['wenxin_card']},'date':'2026-10-26','jobs':{'q':'job'}}
  atomic_json(self.root/'job.json',{'preparation':'insufficient'})
  atomic_json(self.root/'days/2026-10-26/day.json',{'status':'blocked_insufficient_sources'})
  with patch.object(runtime,'job_root',return_value=self.root),patch.object(runtime,'articles',return_value=[{'article':'ready'}]),patch.object(runtime,'resume') as resume:
   self.assertFalse(supplement.refresh(t,'q',self.root,1));resume.assert_not_called()
  atomic_json(self.root/'queue/ticket/ticket.json',{'state':'claimed'})
  with patch.object(runtime,'job_root',return_value=self.root),patch.object(runtime,'articles',return_value=[]),patch.object(runtime,'resume') as resume:
   self.assertFalse(supplement.refresh(t,'q',self.root,1));resume.assert_not_called()
 def test_refresh_archives_and_reprepares(self):
  t={'plan':{'plan_id':'plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','channels':['wenxin_card']},'date':'2026-10-26','jobs':{'q':'job'}}
  atomic_json(self.root/'job.json',{'preparation':'insufficient'})
  atomic_json(self.root/'days/2026-10-26/day.json',{'status':'blocked_insufficient_sources'})
  with patch.object(runtime,'job_root',return_value=self.root),patch.object(runtime,'articles',return_value=[]),patch.object(materials,'records',return_value=[{'question':'q'}]),patch.object(runtime,'resume') as resume:
   self.assertTrue(supplement.refresh(t,'q',self.root,2));resume.assert_called_once()
   self.assertTrue((self.root/'supplement-history/2/day.json').exists())
   self.assertEqual(runtime.read(self.root/'job.json')['supplement_attempt'],2)
   self.assertFalse((self.root/'days/2026-10-26/day.json').exists())
unittest.main()''');p.write_text(s,encoding='utf8')

import sys,tempfile,json,unittest,os
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['/tmp/supplement28-stage','/opt/monitor/geo-content/engine']
from creation import materials,supplement,studio,runtime
from geo_source_cards.runtime import atomic_json
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
 def tearDown(self):self.tmp.cleanup()
 def test_merge_filter_and_dedup(self):
  day='2026-10-26';row={'question':'q','model':'wenxin_card','task_id':'1','captured_at':1}
  for path,rows in [(self.root/'days'/day/'wenxin_card/results.jsonl',[row]),(self.root/'supplements'/day/'q/round-1/days'/day/'wenxin_card/results.jsonl',[row,{**row,'captured_at':2},{**row,'captured_at':3,'body_capture_complete':False},{**row,'question':'other'}])]:
   path.parent.mkdir(parents=True,exist_ok=True);path.write_text('\n'.join(json.dumps(r) for r in rows))
  self.assertEqual(len(materials.records(day,'q',['wenxin_card'],self.root)),2)
 def test_origin(self):
  origin=materials.CONTENT_BASE/'studio/capture/plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
  with patch.dict(os.environ,{'GEO_CREATION_SUPPLEMENT_ORIGIN':str(origin)}):
   self.assertEqual(materials.supplement_origin(origin/'supplements/date/round-1'),origin)
   with self.assertRaises(ValueError):materials.supplement_origin(origin/'days')
 def test_pending_only_materials(self):
  t={'plan':{'questions':['q']},'jobs':{'q':'job'},'date':'2026-10-26'}
  with patch.object(runtime,'job_root',return_value=self.root),patch.object(runtime,'articles',return_value=[]):
   atomic_json(self.root/'days/2026-10-26/day.json',{'status':'blocked_insufficient_sources'})
   self.assertEqual(supplement.pending(t),['q'])
   atomic_json(self.root/'days/2026-10-26/day.json',{'status':'complete_with_failures'})
   self.assertEqual(supplement.pending(t),[])
 def test_scheduler_no_duplicate_and_pause(self):
  cfg={'enabled':True,'start_date':'2026-10-28','include_days':['id']}
  p={'plan_id':'plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','enabled':True,'questions':['q'],'channels':['wenxin_card']}
  t={'plan':p,'daily_task_id':'id','date':'2026-10-26','jobs':{},'skipped_questions':{'q':'none'}}
  atomic_json(self.root/'days/2026-10-26/plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json',t)
  progress=[{'id':'wenxin_card','blocked':{},'settled':0}]
  with patch.object(studio,'ROOT',self.root),patch.object(supplement,'policy',return_value=cfg),patch.object(studio,'plan',return_value=p),patch.object(studio,'capture_root',return_value=self.root/'capture/plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),patch.object(materials,'progress',return_value=progress),patch.object(supplement.subprocess,'run') as run:
   run.return_value.returncode=0
   supplement.tick(100);supplement.tick(101)
   self.assertEqual(run.call_count,1);self.assertEqual(supplement.state(t)['status'],'capturing')
   t['paused']=True;atomic_json(self.root/'days/2026-10-26/plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json',t)
   supplement.tick(102);self.assertEqual(run.call_count,2);self.assertEqual(supplement.state(t)['status'],'paused')
 def test_verification_stops(self):
  cfg={'enabled':True,'start_date':'2026-10-28','include_days':['id']};p={'plan_id':'plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','enabled':True,'questions':['q'],'channels':['wenxin_card']};t={'plan':p,'daily_task_id':'id','date':'2026-10-26','jobs':{},'skipped_questions':{'q':'none'}}
  atomic_json(self.root/'days/2026-10-26/plan-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa.json',t)
  with patch.object(studio,'ROOT',self.root),patch.object(supplement,'policy',return_value=cfg),patch.object(studio,'plan',return_value=p),patch.object(materials,'progress',return_value=[{'id':'wenxin_card','blocked':{'kind':'verification'}}]),patch.object(supplement,'stop') as stop:
   supplement.save(t,{'status':'capturing','root':str(self.root),'channels':['wenxin_card'],'unit':'test'})
   supplement.tick(100);supplement.tick(101)
   stop.assert_called_once();self.assertEqual(supplement.state(t)['status'],'waiting_verification')
 def test_refresh_keeps_completed_and_inflight(self):
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
  with patch.object(runtime,'job_root',return_value=self.root),patch.object(runtime,'articles',return_value=[]),patch.object(materials,'records',return_value=[{'question':'q'}]),patch.object(studio,'capture_root',return_value=self.root),patch.object(runtime,'resume') as resume:
   self.assertTrue(supplement.refresh(t,'q',self.root,2));resume.assert_called_once()
   self.assertTrue((self.root/'supplement-history/2/day.json').exists())
   self.assertEqual(runtime.read(self.root/'job.json')['supplement_attempt'],2)
   self.assertFalse((self.root/'days/2026-10-26/day.json').exists())
unittest.main()



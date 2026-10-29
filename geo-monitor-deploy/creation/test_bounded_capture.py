import tempfile,unittest,sqlite3,os
from pathlib import Path
from unittest.mock import patch,MagicMock
from .search_capture import BoundedRecovery,bounded_automatic,settle_failed_reads
from geo_source_cards.journal import Journal
from .test_studio import StudioTests
from . import studio,materials,runtime
from datetime import datetime

class BoundedTests(unittest.TestCase):
 def test_three_failures_stay_terminal_across_restart_without_fake_success(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GEO_UNATTENDED':'1'}):
   root=Path(tmp);j=Journal(root/'tasks.sqlite');tasks=j.plan('fixture','wenxin_card',['question'],1,root/'results.jsonl');task=dict(tasks[0]);r=BoundedRecovery(j,root)
   for i in range(3):
    with j.db:j.db.execute("update captures set state='capturing' where task_id=?",(task['task_id'],))
    result=r.failure(task,RuntimeError('Required source links are missing'))
    self.assertEqual(result['exhausted'],i==2)
   bounded_automatic(j,'fixture')
   self.assertEqual(j.db.execute('select state from captures').fetchone()[0],'failed_deferred')
   self.assertEqual(j.db.execute("select count(*) from captures where state='completed'").fetchone()[0],0);j.close()

class PartialStudioTests(StudioTests):
 def test_settled_missing_does_not_block_usable_questions(self):
  p=studio.plan(self.plan()['plan_id']);progress=[{'id':m,'completed':1,'settled':2,'failed':1} for m in p['channels']]
  def records(day,q,*args,**kwargs):return [{'body':'verified','sources':[{'url':'https://example.com'}]}] if q==p['questions'][0] else []
  with patch.object(materials,'progress',return_value=progress),patch.object(materials,'records',side_effect=records),patch.object(runtime,'action',return_value={'job_id':'one'}) as create:
   for i in range(3):studio.advance(p,'2099-10-17',datetime(2099,10,17,1,tzinfo=studio.ZONE))
   self.assertEqual(create.call_count,1)
  day=runtime.read(studio.day_path(p['plan_id'],'2099-10-17'));self.assertIn(p['questions'][1],day['skipped_questions'])

class InsufficientTests(unittest.TestCase):
 def test_shortfall_finishes_without_model_call_or_infinite_preparation_retry(self):
  from . import worker,parallel
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);job={'date':'2026-10-26','preparation':'pending'};runtime.atomic_json(root/'job.json',job)
   with patch.object(materials,'prepare',side_effect=materials.InsufficientMaterials('0篇完整正文')),patch.object(worker,'SharedBudget',return_value=MagicMock()),patch.object(worker,'CreationClient') as client:
    worker.execute(root,job,{})
   client.assert_not_called();self.assertEqual(runtime.read(root/'days/2026-10-26/day.json')['status'],'blocked_insufficient_sources');self.assertFalse(parallel.eligible(root))

import sys,tempfile,json,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/opt/monitor/geo-capture']
import question_only_worker as w
class Stops(unittest.TestCase):
 def test_three_identical_errors_stop_without_resend(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d)/'batch';root.mkdir()
   q=w.Queue(root/'tasks.sqlite');q.enqueue('fixture',['问题'],True);t=q.next_task();q.prepare(t['task_id'],protocol='phase-v2');q.click_attempt(t['task_id']);q.db.close()
   reader=Mock();reader.lookup.side_effect=w.DataError('different user turn')
   delivery=Mock();delivery.sync.return_value={'captured':0,'geo_processed':0,'delivery_errors':[]}
   android=Mock();guard=Mock();guard.check.return_value=None
   memory=Mock();memory.maintain.return_value=None;memory.refresh.return_value={}
   config={'batch':'fixture','questions':['问题'],'rounds':1,'interval':60,'model':'doubao1','container':'fixture','serial':'fixture'}
   with patch.object(w,'DoubaoReader',return_value=reader),patch.object(w,'DoubaoDelivery',return_value=delivery),patch.object(w,'make_android',return_value=android),patch.object(w,'native_auth_required',return_value=False),patch.object(w,'AppReadbackGuard',return_value=guard),patch.object(w,'MemoryGuard',return_value=memory),patch.object(w,'wait_seconds'),patch.object(w,'STOP',False):
    self.assertEqual(w.run_locked(config,root,0),0)
   self.assertEqual(reader.lookup.call_count,3);android.send.assert_not_called()
   self.assertEqual(json.loads((root/'bridge_health.json').read_text())['status'],'needs_attention')
unittest.main()

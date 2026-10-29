import tempfile,unittest
from pathlib import Path
from unittest.mock import MagicMock,patch
from . import worker,materials,runtime
from geo_source_cards.deepseek_api import APIError

class EndLoop(Exception):pass

class RecoveryTests(unittest.TestCase):
 def setup_root(self,tmp,preparation):
  base=Path(tmp);root=base/'runs/creation-1000-aabbccdd'
  runtime.atomic_json(root/'job.json',{'job_id':root.name,'date':'2026-10-20','preparation':preparation})
  runtime.atomic_json(root/'control.json',{'paused':False,'revision':1})
  return base,root
 def test_readonly_source_retry_survives_restart_and_does_not_send_paid_call(self):
  with tempfile.TemporaryDirectory() as tmp:
   base,root=self.setup_root(tmp,'pending')
   with patch.object(worker,'BASE',base),patch.object(worker,'SharedBudget',return_value=MagicMock()),patch.object(materials,'prepare',side_effect=ValueError('专用素材仅有0篇完整媒体正文，至少需要3篇')) as prepare,patch.object(worker,'pause') as pause,patch.object(worker,'Worker') as engine:
    worker.execute_once(root)
    self.assertEqual(runtime.read(root/'preparation_retry.json')['attempts'],1)
    worker.execute_once(root)
    self.assertEqual(prepare.call_count,1);engine.assert_not_called();pause.assert_not_called()
 def test_uncertain_paid_execution_is_paused_and_never_automatically_replayed(self):
  with tempfile.TemporaryDirectory() as tmp:
   base,root=self.setup_root(tmp,'ready')
   with patch.object(worker,'BASE',base),patch.object(worker,'SharedBudget',return_value=MagicMock()),patch.object(worker,'CreationClient'),patch.object(worker,'Worker') as engine,patch.object(worker,'pause') as pause:
    engine.return_value.once.side_effect=APIError('request_unknown',uncertain=True)
    worker.execute_once(root)
    self.assertEqual(engine.return_value.once.call_count,1);self.assertEqual(pause.call_args[0][1],'api_unknown')

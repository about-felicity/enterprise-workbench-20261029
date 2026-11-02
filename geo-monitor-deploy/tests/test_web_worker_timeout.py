import sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'geo-source-card-collectors'))
import capture_bridge as bridge
class WebWorkerTimeoutTests(unittest.TestCase):
 def test_deepseek_and_native_never_terminated_by_web_deadline(self):
  for model in ['deepseek','deepseek2','yuanbao','doubao']:
   self.assertEqual(bridge.web_worker_timeout({'model':model},0,99999,0),'')
 def test_normal_rate_wait_and_capture_have_time_to_finish(self):
  self.assertEqual(bridge.web_worker_timeout({'model':'wenxin_card','interval':60},0,359),'')
  self.assertEqual(bridge.web_worker_timeout({'model':'baidu_ai','interval':600},0,839),'')
 def test_worker_capture_hang_is_bounded(self):
  self.assertEqual(bridge.web_worker_timeout({'model':'wenxin_card','interval':60},0,360),'capture_timeout')
 def test_hanging_cleanup_after_durable_capture_has_own_deadline(self):
  cfg={'model':'baidu_ai'}
  self.assertEqual(bridge.web_worker_timeout(cfg,0,200,100),'')
  self.assertEqual(bridge.web_worker_timeout(cfg,0,220,100),'cleanup_timeout')
 def test_termination_waits_then_escalates_only_same_worker_group(self):
  child=Mock(pid=123456);child.wait.side_effect=[bridge.subprocess.TimeoutExpired('worker',10),0]
  with patch.object(bridge.os,'killpg') as kill:
   bridge.terminate_worker(child)
  self.assertEqual([c.args for c in kill.call_args_list],[(123456,bridge.signal.SIGTERM),(123456,bridge.signal.SIGKILL)])
if __name__=='__main__':unittest.main()

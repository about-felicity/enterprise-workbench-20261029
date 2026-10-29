import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
import importlib.util
spec=importlib.util.spec_from_file_location('creation.resume_candidate','/tmp/recovery-runtime-resume.py')
runtime=importlib.util.module_from_spec(spec);spec.loader.exec_module(runtime)
class ResumeTests(unittest.TestCase):
 def test_explicit_resume_clears_stale_budget_wait(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   runtime.atomic_json(root/'control.json',{'paused':True,'revision':4})
   runtime.atomic_json(root/'known_preflight_retry.json',{'state':'waiting','code':'budget_exceeded','budget_pause':True,'control_revision':2,'next_at':9999999999})
   with patch.object(runtime,'assert_job_controllable'):
    runtime.resume(root,check_balance=False)
   self.assertTrue(recovery.ready(root));self.assertFalse(runtime.read(root/'control.json')['paused'])
 def test_nested_unknown_request_is_not_replayed(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   runtime.atomic_json(root/'control.json',{'paused':True,'revision':4})
   runtime.atomic_json(root/'api/active.json',{'run_id':'abc','state':'REQUESTING'})
   runtime.atomic_json(root/'api/runs/abc/skeleton-call/api_state.json',{'state':'REQUEST_UNKNOWN'})
   with patch.object(runtime,'assert_job_controllable'),self.assertRaises(ValueError):runtime.resume(root,check_balance=False)
   self.assertTrue(runtime.read(root/'control.json')['paused'])
if __name__=='__main__':unittest.main()

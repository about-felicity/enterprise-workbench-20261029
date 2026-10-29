import tempfile,unittest
from pathlib import Path
from geo_source_cards.runtime import atomic_json
from .editorial_status import execution_health

class HealthTests(unittest.TestCase):
 def test_historical_requesting_is_not_active_after_completion_or_failure(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);atomic_json(root/'api/health.json',{'status':'requesting','state':'REQUESTING'})
   self.assertEqual(execution_health(root,[],{'status':'complete'})['status'],'complete')
   h=execution_health(root,[{'state':'needs_attention'}],{});self.assertEqual(h['status'],'completed_with_failures');self.assertFalse(h['active_execution']);self.assertEqual(h['historical_observation']['state'],'REQUESTING')
 def test_saved_response_is_never_reported_as_request_in_flight(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);atomic_json(root/'api/active.json',{'state':'RESPONDED','run_id':'r'})
   self.assertEqual(execution_health(root,[],{})['status'],'response_saved')
 def test_actual_unknown_request_remains_protected(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);atomic_json(root/'api/active.json',{'state':'REQUESTING','run_id':'r'});atomic_json(root/'api/runs/r/call/api_state.json',{'state':'REQUEST_UNKNOWN'})
   h=execution_health(root,[],{});self.assertEqual(h['status'],'request_unknown');self.assertTrue(h['active_execution'])
 def test_pending_queue_not_falsely_completed(self):
  with tempfile.TemporaryDirectory() as tmp:self.assertEqual(execution_health(Path(tmp),[{'state':'pending'}],{})['status'],'queued')

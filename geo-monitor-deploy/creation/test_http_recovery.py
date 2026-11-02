import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from . import recovery,runtime
from geo_source_cards.daily_editorial import publish_ticket

class HTTPRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
  self.location=self.root/'work';runtime.atomic_json(self.location/'input.json',{'value':'unchanged'})
  self.ticket=publish_ticket(self.root,'research',self.location,['input.json'],[],{'date':'2026-10-29','category':'test','number':1})
  ticket_path=self.root/'queue'/self.ticket/'ticket.json';ticket=runtime.read(ticket_path)
  runtime.atomic_json(ticket_path,{**ticket,'state':'claimed'})
  runtime.atomic_json(self.root/'control.json',{'paused':True,'reason':'api_unknown','revision':1})
  runtime.atomic_json(self.root/'api/active.json',{'state':'REQUESTING','run_id':'original','ticket':self.ticket,'stage':'research'})
  self.call=self.root/'api/runs/original/skeleton-call'
  runtime.atomic_json(self.call/'api_state.json',{'state':'HTTP_REJECTED','http_status':502,'reservation':'keep-billing-reservation'})
  runtime.atomic_json(self.call/'request.json',{'messages':['paid input']})
 def tearDown(self):self.temp.cleanup()
 def test_replacement_preserves_original_evidence_and_is_idempotent(self):
  original={p.name:p.read_bytes() for p in self.call.iterdir()}
  replacement=recovery.recover_http_failure(self.root)
  self.assertNotEqual(replacement,self.ticket)
  self.assertEqual({p.name:p.read_bytes() for p in self.call.iterdir()},original)
  self.assertEqual(runtime.read(self.root/'queue'/self.ticket/'ticket.json')['replaced_by'],replacement)
  self.assertEqual(runtime.read(self.root/'queue'/replacement/'ticket.json')['meta']['operator_http_retries'],1)
  self.assertIsNone(recovery.recover_http_failure(self.root))
  self.assertTrue(recovery.safe_original(self.root))
  self.assertEqual(len(list((self.root/'queue').glob('*/ticket.json'))),2)
 def test_unknown_delivery_is_never_replaced(self):
  runtime.atomic_json(self.call/'api_state.json',{'state':'REQUEST_UNKNOWN','reservation':'keep'})
  self.assertFalse(recovery.safe_original(self.root));self.assertIsNone(recovery.recover_http_failure(self.root))
  self.assertEqual(len(list((self.root/'queue').glob('*/ticket.json'))),1)
 def test_http_gateway_failure_does_not_pass_ordinary_resume_gate(self):
  self.assertFalse(recovery.safe_original(self.root))
  with patch.object(runtime,'assert_job_controllable'):
   with self.assertRaisesRegex(ValueError,'未知'):runtime.resume(self.root,check_balance=False)
  self.assertEqual(len(list((self.root/'queue').glob('*/ticket.json'))),1)
 def test_saved_response_needs_no_replacement(self):
  runtime.atomic_json(self.call/'response.json',{'answer':'already paid'})
  self.assertTrue(recovery.safe_original(self.root));self.assertIsNone(recovery.recover_http_failure(self.root))
 def test_second_operator_replacement_is_blocked(self):
  replacement=recovery.recover_http_failure(self.root)
  runtime.atomic_json(self.root/'api/active.json',{'state':'REQUESTING','run_id':'retry','ticket':replacement,'stage':'research'})
  runtime.atomic_json(self.root/'api/runs/retry/call/api_state.json',{'state':'HTTP_REJECTED','http_status':503})
  with self.assertRaisesRegex(ValueError,'补做过一次'):recovery.recover_http_failure(self.root)
  self.assertEqual(len(list((self.root/'queue').glob('*/ticket.json'))),2)
 def test_running_execution_cannot_be_replaced(self):
  runtime.atomic_json(self.root/'control.json',{'paused':False})
  with self.assertRaisesRegex(ValueError,'尚未暂停'):recovery.recover_http_failure(self.root)

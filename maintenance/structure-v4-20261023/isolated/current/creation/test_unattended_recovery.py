import tempfile,unittest
from pathlib import Path
from geo_source_cards.deepseek_api import APIError
from geo_source_cards.runtime import atomic_json
from . import recovery,runtime

class UnattendedRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  atomic_json(self.root/'control.json',{'paused':False,'revision':2})
  atomic_json(self.root/'api/active.json',{'state':'REQUESTING','run_id':'original'})
 def test_readonly_failure_backs_off_durably_without_clearing_original(self):
  self.assertTrue(recovery.defer(self.root,APIError('balance_unavailable'),now=100))
  self.assertFalse(recovery.ready(self.root,now=101));self.assertTrue(recovery.ready(self.root,now=130))
  self.assertEqual(runtime.read(self.root/'api/active.json')['run_id'],'original')
  self.assertTrue(recovery.defer(self.root,APIError('balance_http_503'),now=130))
  self.assertFalse(recovery.ready(self.root,now=189));self.assertTrue(recovery.ready(self.root,now=190))
 def test_unknown_paid_or_logic_call_never_becomes_a_preflight_retry(self):
  for folder in ('call','logic-call'):
   p=self.root/'api/runs/original'/folder/'api_state.json';atomic_json(p,{'state':'REQUEST_UNKNOWN'})
   self.assertFalse(recovery.defer(self.root,APIError('balance_unavailable'),now=100));p.unlink()
  self.assertFalse(recovery.defer(self.root,APIError('network_delivery_unknown',uncertain=True),now=100))
 def test_budget_resume_requires_same_internal_pause_revision(self):
  atomic_json(self.root/'control.json',{'paused':True,'revision':3,'reason':'budget'})
  self.assertTrue(recovery.defer(self.root,APIError('budget_exceeded'),now=100))
  after=runtime.read(self.root/'known_preflight_retry.json')['next_at']
  self.assertFalse(recovery.ready(self.root,now=after-1));self.assertTrue(recovery.ready(self.root,now=after))
  self.assertFalse(runtime.read(self.root/'control.json')['paused'])
  atomic_json(self.root/'control.json',{'paused':True,'revision':8,'reason':'budget'})
  self.assertTrue(recovery.defer(self.root,APIError('budget_exceeded'),now=after))
  atomic_json(self.root/'control.json',{'paused':True,'revision':9,'reason':'operator'})
  self.assertFalse(recovery.ready(self.root,now=after+90000));self.assertTrue(runtime.read(self.root/'control.json')['paused'])
 def test_operator_pause_is_never_replaced_with_auto_recovery(self):
  atomic_json(self.root/'control.json',{'paused':True,'revision':4,'reason':'operator'})
  self.assertFalse(recovery.defer(self.root,APIError('balance_unavailable'),now=100))
  self.assertFalse(recovery.defer(self.root,APIError('budget_exceeded'),now=100))

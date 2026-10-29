import copy,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock,patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from draft_submission_recovery import absent_proof,exact_draft,recover
from unattended_worker import atomic_json

XML='<hierarchy><node resource-id="com.larus.nova:id/back_icon" content-desc="返回"/><node resource-id="com.larus.nova:id/input_text" text="问题"/><node resource-id="com.larus.nova:id/action_send" enabled="true"/></hierarchy>'


class DraftRecoveryTests(unittest.TestCase):
 def setUp(self):
  stable=patch('draft_submission_recovery.stabilize_question_only_send');self.stable=stable.start();self.addCleanup(stable.stop)
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.before={'databases':[{'database':'db','conversations':['old'],'prior_requests':[{'id':'old'}],'max_rowid':2}]}
  self.task={'task_id':'task','question':'问题','wire_question':'问题','state':'prepared','prepared_at':10,'capture_retries':0}
  atomic_json(self.root/'task-attempt-0.pre-send.json',self.before)
  self.device=Mock();self.device.app_current.return_value={'package':'com.larus.nova'};self.device.dump_hierarchy.return_value=XML
  self.android=SimpleNamespace(device=self.device,tap=Mock());self.event=Mock()
 def run_recovery(self,now=200,**kw):
  with patch('draft_submission_recovery.baseline',return_value=self.before):return recover(self.root,self.task,{'status':'absent'},self.android,['db'],self.event,clock=lambda:now,**kw)
 def test_local_unacknowledged_request_already_blocks_a_second_tap(self):
  after=copy.deepcopy(self.before);after['databases'][0]['prior_requests'].append({'id':'new-local'})
  self.assertIsNone(absent_proof(self.before,after))
  after=copy.deepcopy(self.before);after['databases'][0]['conversations'].append('new')
  self.assertIsNone(absent_proof(self.before,after))
 def test_missing_legacy_baseline_or_changed_database_is_not_proof(self):
  after=copy.deepcopy(self.before);after['databases'][0]['database']='different'
  self.assertIsNone(absent_proof(self.before,after))
  old=copy.deepcopy(self.before);del old['databases'][0]['prior_requests']
  self.assertIsNone(absent_proof(old,self.before))
 def test_two_observations_allow_one_existing_draft_tap_across_restarts(self):
  self.assertEqual(self.run_recovery()['phase'],'verifying_existing_draft');self.android.tap.assert_not_called()
  self.assertEqual(self.run_recovery(211)['phase'],'awaiting_existing_draft_ack');self.assertEqual(self.android.tap.call_count,1)
  self.assertIsNone(self.run_recovery(300));self.assertEqual(self.android.tap.call_count,1)
  self.device.assert_called_once_with(resourceId='com.larus.nova:id/action_send')
 def test_pause_stop_binding_wrong_draft_and_ack_never_tap(self):
  self.assertIsNone(self.run_recovery(paused=True));self.assertIsNone(self.run_recovery(stopping=True))
  self.task['request_id']='request';self.assertIsNone(self.run_recovery());del self.task['request_id']
  atomic_json(self.root/'task-attempt-0.binding.json',{'id':'bound'});self.assertIsNone(self.run_recovery())
  self.android.tap.assert_not_called()
  self.assertFalse(exact_draft(XML.replace('text="问题"','text="不同草稿"'),'问题'))
  self.assertFalse(exact_draft(XML.replace('</hierarchy>','<node resource-id="com.larus.nova:id/md_text"/></hierarchy>'),'问题'))
 def test_new_request_between_two_observations_cancels_recovery(self):
  self.run_recovery();after=copy.deepcopy(self.before);after['databases'][0]['prior_requests'].append({'id':'late-local'})
  with patch('draft_submission_recovery.baseline',return_value=after):
   self.assertIsNone(recover(self.root,self.task,{'status':'absent'},self.android,['db'],self.event,clock=lambda:211))
  self.android.tap.assert_not_called()
 def test_controller_original_drain_allows_only_existing_draft_but_user_pause_does_not(self):
  atomic_json(self.root/'maintenance_pause.json',{'source':'daily_tasks','action':'apply','allow_original_readback':True})
  self.run_recovery();self.assertEqual(self.run_recovery(211)['phase'],'awaiting_existing_draft_ack')
  self.assertEqual(self.android.tap.call_count,1)
 def test_user_pause_arriving_after_first_proof_cancels_tap(self):
  self.run_recovery();atomic_json(self.root/'maintenance_pause.json',{'source':'user','action':'pause'})
  self.assertIsNone(self.run_recovery(211));self.android.tap.assert_not_called()
 def test_recovered_submit_respects_and_updates_device_send_interval(self):
  last=self.root/'last-send.json';atomic_json(last,{'time':190})
  self.assertIsNone(self.run_recovery(last_send_path=last,interval=45))
  self.run_recovery(240,last_send_path=last,interval=45)
  self.assertEqual(self.run_recovery(251,last_send_path=last,interval=45)['phase'],'awaiting_existing_draft_ack')
  self.assertEqual(json.loads(last.read_text())['time'],251)

 def newline_draft(self,text='问题\n'):
  xml=XML.replace('text="问题"','text="'+text.replace('\n','&#10;')+'"')
  self.device.dump_hierarchy.return_value=xml
  self.device.return_value.set_text.side_effect=lambda *a,**k:setattr(self.device.dump_hierarchy,'return_value',XML)

 def test_exact_single_trailing_newline_is_normalized_once_then_submitted(self):
  self.newline_draft();self.assertEqual(self.run_recovery()['phase'],'verifying_existing_draft')
  self.device.return_value.set_text.assert_not_called()
  self.assertEqual(self.run_recovery(211)['phase'],'awaiting_existing_draft_ack')
  self.device.return_value.set_text.assert_called_once_with('问题',timeout=5)
  self.android.tap.assert_called_once();self.stable.assert_called_once_with(self.device,'问题')
  state=json.loads((self.root/'task-attempt-0.draft-submit-recovery.json').read_text())
  self.assertEqual(state['original_draft'],'问题\n');self.assertTrue(state['normalization_attempted']);self.assertTrue(state['attempted'])
  self.run_recovery(300);self.assertEqual(self.android.tap.call_count,1)

 def test_other_whitespace_changed_text_and_double_newline_are_not_normalized(self):
  for text in ('问题\n\n','问题 ',' 问题','问题不同\n'):
   self.newline_draft(text);self.assertIsNone(self.run_recovery(300))
  self.device.return_value.set_text.assert_not_called();self.android.tap.assert_not_called()

 def test_newline_cleanup_forbidden_when_a_local_request_or_user_pause_arrives(self):
  self.newline_draft();self.run_recovery()
  atomic_json(self.root/'maintenance_pause.json',{'source':'user','action':'pause'})
  self.assertIsNone(self.run_recovery(211));self.device.return_value.set_text.assert_not_called()
  (self.root/'maintenance_pause.json').unlink()
  after=copy.deepcopy(self.before);after['databases'][0]['prior_requests'].append({'id':'local-unacknowledged'})
  with patch('draft_submission_recovery.baseline',return_value=after):
   self.assertIsNone(recover(self.root,self.task,{'status':'absent'},self.android,['db'],self.event,clock=lambda:300))
  self.device.return_value.set_text.assert_not_called();self.android.tap.assert_not_called()

 def test_late_request_after_normalization_blocks_send(self):
  self.newline_draft();self.run_recovery();after=copy.deepcopy(self.before);after['databases'][0]['prior_requests'].append({'id':'late'})
  with patch('draft_submission_recovery.baseline',side_effect=[self.before,self.before,after]):
   self.assertIsNone(recover(self.root,self.task,{'status':'absent'},self.android,['db'],self.event,clock=lambda:211))
  self.device.return_value.set_text.assert_called_once();self.android.tap.assert_not_called()

 def test_failed_normalization_is_never_repeated_after_restart(self):
  self.newline_draft();self.device.return_value.set_text.side_effect=None;self.run_recovery()
  self.assertIsNone(self.run_recovery(211));self.assertIsNone(self.run_recovery(300))
  self.device.return_value.set_text.assert_called_once();self.android.tap.assert_not_called()

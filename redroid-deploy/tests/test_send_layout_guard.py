import sys,unittest
from pathlib import Path
from unittest.mock import Mock
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from question_only_adapters import stabilize_question_only_send
from unattended_core import DataError
XML='<hierarchy><node resource-id="com.larus.nova:id/back_icon" content-desc="返回"/><node resource-id="com.larus.nova:id/input_text" text="问题"/><node resource-id="com.larus.nova:id/action_send" enabled="true" bounds="[608,1000][696,1100]"/></hierarchy>'
IME=XML.replace('</hierarchy>','<node package="com.android.inputmethod.latin"/></hierarchy>')
class SendLayoutGuardTests(unittest.TestCase):
 def run_guard(self,device,timeout=3):
  now=[0]
  def sleep(v):now[0]+=v
  return stabilize_question_only_send(device,'问题',timeout=timeout,clock=lambda:now[0],sleep=sleep)
 def test_keyboard_closed_once_and_three_stable_observations_required(self):
  d=Mock();d.dump_hierarchy.side_effect=[IME,IME,XML,XML,XML]
  self.run_guard(d);d.press.assert_called_once_with('back');self.assertEqual(d.dump_hierarchy.call_count,5)
 def test_moving_target_resets_observation_count(self):
  d=Mock();d.dump_hierarchy.side_effect=[XML,XML.replace('1000','900'),XML,XML,XML]
  self.run_guard(d);self.assertEqual(d.dump_hierarchy.call_count,5);d.press.assert_not_called()
 def test_keyboard_never_disappears_times_out_without_repeated_back(self):
  d=Mock();d.dump_hierarchy.return_value=IME
  with self.assertRaises(DataError):self.run_guard(d,1)
  d.press.assert_called_once_with('back')
 def test_changed_draft_or_existing_chat_is_rejected(self):
  for xml in [XML.replace('text="问题"','text="问题&#10;"'),XML.replace('</hierarchy>','<node resource-id="com.larus.nova:id/md_text"/></hierarchy>'),XML.replace('enabled="true"','enabled="false"')]:
   d=Mock();d.dump_hierarchy.return_value=xml
   with self.assertRaises(DataError):self.run_guard(d)
   d.press.assert_not_called()

import json,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[2]/'redroid-deploy')]
from draft_recovery import recover
from android_ui import PACKAGE,draft_matches,stable_send_button

class DraftRecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.task=dict(task_id='t',state='prepared',wire_question='问题',prepared_at=100,request_id=None)
  (self.root/'t.pre-send.json').write_text(json.dumps(dict(baseline_mode='ids_only_with_persisted_history',conversations=['old'])))
  with sqlite3.connect(self.root/'tasks.sqlite') as db:
   db.execute('create table events(task_id,event)');db.execute("insert into events values('t','send_click_intent_committed')")
  db.close()
  self.a=Mock();self.a.device.app_current.return_value={'package':PACKAGE,'pid':1}
  self.a.device.dump_hierarchy.return_value=f'<hierarchy><node class="android.widget.EditText" package="{PACKAGE}" text="问题"/><node content-desc="临时对话模式开关-关"/></hierarchy>'
  self.a.device.return_value.get_text.return_value='问题'
  self.r=Mock();self.r.script.exports_sync.conversation_ids.return_value=['old'];self.r.script.exports_sync.snapshot.return_value=[]
  self.event=Mock();self.button=Mock();self.button.info={'bounds':{'left':1}}
 def call(self,at,**kwargs):
  with patch('draft_recovery.time.time',return_value=at),patch('draft_recovery.history_index',return_value=[[{'id':'old'}]]),patch('draft_recovery.stable_send_button',return_value=(self.button,self.button.info['bounds'])):
   return recover(self.root,self.task,{'status':'absent'},self.a,self.r,self.event,**kwargs)
 def test_two_observations_then_only_one_tap(self):
  self.assertEqual(self.call(300)['phase'],'verifying_existing_draft');self.a.tap.assert_not_called()
  self.assertEqual(self.call(320)['phase'],'awaiting_existing_draft_ack');self.a.tap.assert_called_once()
  self.call(400);self.a.tap.assert_called_once()
 def test_new_native_conversation_prevents_submit(self):
  self.call(300);self.r.script.exports_sync.conversation_ids.return_value=['old','new']
  self.assertIsNone(self.call(320));self.a.tap.assert_not_called()
 def test_native_render_prevents_submit(self):
  self.r.script.exports_sync.snapshot.return_value=[{}];self.assertIsNone(self.call(300));self.a.tap.assert_not_called()
 def test_bound_and_paused_prevent_submit(self):
  self.assertIsNone(self.call(300,paused=True))
  (self.root/'t.binding.json').write_text('{}');self.assertIsNone(self.call(400));self.a.tap.assert_not_called()
 def test_pause_between_observations_prevents_submit(self):
  self.call(300);(self.root/'maintenance_pause.json').write_text('{}');self.assertIsNone(self.call(320));self.a.tap.assert_not_called()
 def test_process_change_restarts_observation(self):
  self.call(300);self.a.device.app_current.return_value={'package':PACKAGE,'pid':2}
  self.assertEqual(self.call(320)['phase'],'verifying_existing_draft');self.a.tap.assert_not_called()
 def test_relaunch_and_duplicate_click_are_not_recoverable(self):
  with sqlite3.connect(self.root/'tasks.sqlite') as db:
   db.execute("insert into events values('t','native_app_relaunch_for_readback')")
  db.close();self.assertIsNone(self.call(300));self.a.tap.assert_not_called()
  with sqlite3.connect(self.root/'tasks.sqlite') as db:
   db.execute("delete from events where event='native_app_relaunch_for_readback'")
   db.execute("insert into events values('t','send_click_intent_committed')")
  db.close();self.assertIsNone(self.call(320));self.a.tap.assert_not_called()
 def test_other_draft_not_eligible(self):
  self.assertFalse(draft_matches(self.a.device.dump_hierarchy(), '其他问题'))
 def test_stable_send_hides_keyboard(self):
  d=Mock();d.info={'currentPackageName':PACKAGE};d.shell.return_value.output='mInputShown=true'
  d.return_value.count=1;d.return_value.get_text.return_value='问题';d.return_value.info={'bounds':{'left':1},'enabled':True}
  with patch('android_ui.time.sleep'):stable_send_button(d,'问题')
  d.press.assert_called_once_with('back')

if __name__=='__main__':unittest.main()

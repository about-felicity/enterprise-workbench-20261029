import json,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from unbound_history import candidate,recover,send_proof

class RecoveryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)/'batches/current';self.root.mkdir(parents=True)
  self.task={'state':'prepared','task_id':'task','prepared_at':100,'wire_question':'原问题','question':'原问题','request_id':None,'capture_retries':0}
  (self.root/'task.pre-send.json').write_text(json.dumps({'protocol':'question-only-v1','created_at':95,'conversations':['old']}))
  with sqlite3.connect(self.root/'tasks.sqlite') as db:
   db.execute('create table events(task_id,event,time)');db.execute('insert into events values(?,?,?)',('task','send_click_intent_committed',100))
   db.execute('insert into events values(?,?,?)',('task','native_app_relaunch_for_readback',105))
  self.rows=[{'id':'new','title':'原问题生成的标题','last_replied_at':115},{'id':'old','title':'上一题','last_replied_at':90},{'id':'older','title':'更早问题','last_replied_at':70}]
 def test_single_fresh_unclaimed_candidate_does_not_require_title_to_equal_prompt(self):
  base=json.loads((self.root/'task.pre-send.json').read_text())
  self.assertEqual(candidate([self.rows],base,100,[])['conversation_id'],'new')
  self.assertEqual(candidate([self.rows],base,100,['new']),None)
 def test_ambiguous_old_outside_window_or_duplicate_title_is_not_a_candidate(self):
  base={'conversations':['old']}
  for rows in (self.rows+[{'id':'other','title':'别题','last_replied_at':119}],
               [{**self.rows[0],'last_replied_at':500}],
               [{**self.rows[0],'id':'old'}]):
   self.assertIsNone(candidate([rows],base,100,[]))
  # Old duplicate titles do not prove identity. Visible order and exactly one
  # selectable title must still pass before any read-only navigation.
  rows=self.rows+[{'id':'other','title':self.rows[0]['title'],'last_replied_at':20}]
  self.assertEqual(candidate([rows],base,100,[])['conversation_id'],'new')
 def test_missing_or_duplicate_click_proof_never_allows_navigation(self):
  self.assertIsNotNone(send_proof(self.root,self.task))
  with sqlite3.connect(self.root/'tasks.sqlite') as db:db.execute('insert into events values(?,?,?)',('task','send_click_intent_committed',101))
  self.assertIsNone(send_proof(self.root,self.task))
 def test_bound_request_retry_or_other_task_state_never_uses_unbound_recovery(self):
  for changes in ({'request_id':'trace'},{'capture_retries':1},{'state':'pending'}):self.assertIsNone(send_proof(self.root,{**self.task,**changes}))
  (self.root/'task.binding.json').write_text('{}');self.assertIsNone(send_proof(self.root,self.task))
 def test_normal_slow_response_or_relaunch_before_send_never_navigates(self):
  with sqlite3.connect(self.root/'tasks.sqlite') as db:db.execute("update events set time=90 where event='native_app_relaunch_for_readback'")
  self.assertIsNone(send_proof(self.root,self.task))
  android=self.device();index=Mock()
  self.assertIsNone(recover(self.root,self.task,{'status':'absent'},android,Mock(),Mock(),index=index,clock=lambda:130))
  android.tap.assert_not_called();index.assert_not_called()
 def test_missing_history_probe_backoff_survives_restart_without_consuming_navigation_attempt(self):
  android=self.device();index=Mock(return_value=[])
  with patch('unattended_worker.atomic_json',side_effect=lambda p,v:p.write_text(json.dumps(v))):
   result=recover(self.root,self.task,{'status':'absent'},android,Mock(),Mock(),index=index,clock=lambda:130)
   self.assertEqual(result['reason'],'unbound_history_candidate_unproven')
   self.assertIsNone(recover(self.root,self.task,{'status':'absent'},android,Mock(),Mock(),index=index,clock=lambda:140))
   self.assertEqual(index.call_count,1);android.tap.assert_not_called()
   self.assertEqual(json.loads((self.root/'task.unbound-history.json').read_text()).get('attempts',0),0)
 def device(self,draft=False,wrong_order=False):
  class Selector:
   def __init__(self,kind):self.kind=kind;self.count=1
  class Device:
   mode='landing'
   def app_current(self):return {'package':'com.tencent.hunyuan.app.chat'}
   def dump_hierarchy(inner):
    if inner.mode=='landing':return '<hierarchy><node text="Hi，用户"/><node class="android.widget.EditText" text="'+('有草稿' if draft else '')+'"/></hierarchy>'
    titles=[r['title'] for r in self.rows]
    if wrong_order:titles.reverse()
    return '<hierarchy>'+''.join('<node text="'+t+'"/>' for t in titles)+'</hierarchy>'
   def __call__(self,**kwargs):return Selector('drawer' if kwargs.get('description') else 'history')
   def press(self,key):self.mode='landing'
  d=Device();android=Mock();android.device=d
  def tap(selector):d.mode='drawer' if selector.kind=='drawer' else 'chat'
  android.tap.side_effect=tap;return android
 def test_read_only_history_navigation_is_bounded_and_does_not_create_binding(self):
  android=self.device();event=Mock();close=Mock()
  with patch('unattended_worker.atomic_json',side_effect=lambda p,v:p.write_text(json.dumps(v))):
   result=recover(self.root,self.task,{'status':'absent'},android,close,event,index=lambda:[self.rows],clock=lambda:130,sleep=lambda _:None)
   self.assertEqual(result['phase'],'reloading_original_history');self.assertEqual(android.tap.call_count,2)
   self.assertFalse((self.root/'task.binding.json').exists());self.assertFalse(json.loads((self.root/'task.unbound-history.json').read_text())['original_request_confirmed'])
   count=android.tap.call_count;self.assertIsNone(recover(self.root,self.task,{'status':'absent'},android,close,event,index=lambda:[self.rows],clock=lambda:140))
   self.assertEqual(android.tap.call_count,count)
 def test_pause_stop_draft_and_wrong_drawer_never_open_history(self):
  for options in ({'paused':True},{'stopping':True}):
   android=self.device();self.assertIsNone(recover(self.root,self.task,{'status':'absent'},android,Mock(),Mock(),clock=lambda:130,**options));android.tap.assert_not_called()
  android=self.device(draft=True);self.assertIsNone(recover(self.root,self.task,{'status':'absent'},android,Mock(),Mock(),index=lambda:[self.rows],clock=lambda:130));android.tap.assert_not_called()
  (self.root/'task.unbound-history.json').unlink()
  android=self.device(wrong_order=True)
  with patch('unattended_worker.atomic_json',side_effect=lambda p,v:p.write_text(json.dumps(v))):
   result=recover(self.root,self.task,{'status':'absent'},android,Mock(),Mock(),index=lambda:[self.rows],clock=lambda:130,sleep=lambda _:None)
   self.assertEqual(result['reason'],'unbound_drawer_order_unproven');self.assertEqual(android.tap.call_count,1)

if __name__=='__main__':unittest.main()

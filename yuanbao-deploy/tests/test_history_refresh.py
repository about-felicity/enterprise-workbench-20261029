import json,sqlite3,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from history_refresh import stored_history,refresh_original,memory_history,pause_blocks_readback,restore_after_exit,stored_drawer_proof

class HistoryRefreshTests(unittest.TestCase):
 def test_only_daily_original_readback_marker_allows_read_only_navigation(self):
  self.assertFalse(pause_blocks_readback({'source':'daily_tasks','action':'apply','allow_original_readback':True}))
  for marker in ({},{'source':'control_panel','action':'pause','allow_original_readback':True},
                 {'source':'daily_tasks','action':'pause','allow_original_readback':True},
                 {'source':'daily_tasks','action':'apply'}):self.assertTrue(pause_blocks_readback(marker))
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.p=self.root/'chat.db'
  self.task={'task_id':'task','wire_question':'测试问题','state':'prepared','prepared_at':100}
  self.binding={'conversation_id':'cid','server_answer_id':'local_a'};self.raw={'content':{'traceId':'trace'},'question_entities':[{'type':'TEXT','textEntity':{'text':'测试问题'}}]}
  with sqlite3.connect(self.p) as db:
   db.executescript('create table ChatMessages(conversation_id,message_id,message_index,speaker,raw_data);create table ChatMessagesContecnt(conversation_id,message_id,trace_id);create table ChatConversationDetail(conversation_id,title);')
   db.executemany('insert into ChatMessages values(?,?,?,?,?)',[('cid','cid_1',1,'human',json.dumps({'displayPrompt':'测试问题'})),('cid','cid_2',2,'ai','{}')])
   db.execute('insert into ChatMessagesContecnt values(?,?,?)',('cid','cid_2','trace'))
   db.executemany('insert into ChatConversationDetail values(?,?)',[('cid','原会话'),('other','另一会话')])
 def tearDown(self):self.temp.cleanup()
 def test_matching_first_turn_store_is_a_read_only_reload_proof(self):
  with patch('history_refresh.databases',return_value=[self.p]):
   proof=stored_history(self.binding,self.task,self.raw)
  self.assertEqual(proof['title'],'原会话');self.assertEqual(proof['request_id'],'trace')
 def test_other_trace_question_or_extra_turn_is_not_a_match(self):
  with patch('history_refresh.databases',return_value=[self.p]):
   self.assertIsNone(stored_history(self.binding,self.task,{'content':{'traceId':'other'}}))
   self.assertIsNone(stored_history(self.binding,{**self.task,'wire_question':'other'},self.raw))
   with sqlite3.connect(self.p) as db:db.execute('insert into ChatMessages values(?,?,?,?,?)',('cid','cid_3',3,'human','{}'))
   self.assertIsNone(stored_history(self.binding,self.task,self.raw))
 def test_paused_young_or_exhausted_task_never_navigates(self):
  a=Mock();observed={'reason':'native_answer_fetch_failed'}
  for flags in ({'paused':True},{'stopping':True},{'clock':lambda:110}):
   self.assertIsNone(refresh_original(self.root,self.task,observed,a,Mock(),Mock(),**flags))
  (self.root/'task.history-refresh.json').write_text(json.dumps({'attempts':2}))
  self.assertIsNone(refresh_original(self.root,self.task,observed,a,Mock(),Mock(),clock=lambda:1000))
  self.assertFalse(a.mock_calls)
 def test_proven_history_reload_has_no_send_and_is_durably_rate_limited(self):
  (self.root/'task.native.json').write_text(json.dumps(self.raw));(self.root/'task.binding.json').write_text(json.dumps(self.binding))
  a=Mock();a.device.return_value.count=1
  a.device.dump_hierarchy.return_value='<hierarchy><node text="测试问题"/><node text="原会话"/><node text="另一会话"/></hierarchy>'
  proof={'title':'原会话','other_titles':['另一会话'],'request_id':'trace','conversation_id':'cid'}
  close=Mock();event=Mock();observed={'reason':'native_answer_fetch_failed'}
  with patch('history_refresh.stored_history',return_value=proof):
   result=refresh_original(self.root,self.task,observed,a,close,event,clock=lambda:1000,sleep=Mock())
   self.assertEqual(result['phase'],'reloading_original_history');self.assertEqual(a.tap.call_count,4)
   self.assertFalse(a.send.called);close.assert_called_once();event.assert_called_once()
   before=a.tap.call_count
   self.assertIsNone(refresh_original(self.root,self.task,observed,a,close,event,clock=lambda:1001))
   self.assertEqual(a.tap.call_count,before)

 def interrupted(self):
  self.binding.update(task_id='task',server_answer_id='cid_2')
  self.task['request_id']='trace'
  self.raw.update(message={'id':'a','serverId':'cid_2','pairId':'q','serverPairId':'cid_1',
    'speaker':'AI','serverIndex':2,'contentCount':1,'state':'INTERRUPTED'},
    question={'id':'q','serverId':'cid_1','speaker':'HUMAN','serverIndex':1},conversation={'isBusy':False})
  self.raw['content']['state']='INTERRUPTED'
  return [{'conversation_id':'cid','title':'原会话'}]

 def test_failed_placeholder_can_reveal_question_with_durable_scroll_limit(self):
  (self.root/'task.native.json').write_text(json.dumps(self.raw));(self.root/'task.binding.json').write_text(json.dumps(self.binding))
  a=Mock();a.device.window_size.return_value=(720,1280);a.device.app_current.return_value={'package':'com.tencent.hunyuan.app.chat'}
  a.device.dump_hierarchy.return_value='<hierarchy><node text="回答拉取失败，正在重试"/></hierarchy>'
  proof={'title':'原会话','other_titles':['另一会话'],'request_id':'trace','conversation_id':'cid'}
  with patch('history_refresh.stored_history',return_value=proof):
   for at in [1000,1061,1122]:
    result=refresh_original(self.root,self.task,{'reason':'native_answer_fetch_failed'},a,Mock(),Mock(),clock=lambda:at,sleep=Mock())
    self.assertEqual(result['phase'],'revealing_original_question')
   self.assertIsNone(refresh_original(self.root,self.task,{'reason':'native_answer_fetch_failed'},a,Mock(),Mock(),clock=lambda:1183,sleep=Mock()))
  self.assertEqual(a.device.swipe.call_count,3);a.tap.assert_not_called();a.send.assert_not_called()

 def test_draft_blocks_reveal_scroll(self):
  (self.root/'task.native.json').write_text(json.dumps(self.raw));(self.root/'task.binding.json').write_text(json.dumps(self.binding))
  a=Mock();a.device.dump_hierarchy.return_value='<hierarchy><node text="回答拉取失败，正在重试"/><node class="android.widget.EditText" text="草稿"/></hierarchy>'
  with patch('history_refresh.stored_history',return_value={'title':'原会话'}):
   self.assertIsNone(refresh_original(self.root,self.task,{'reason':'native_answer_fetch_failed'},a,Mock(),Mock(),clock=lambda:1000,sleep=Mock()))
  a.device.swipe.assert_not_called()

 def test_only_proven_local_fetch_placeholder_can_have_index_one(self):
  from history_refresh import original_pair_matches
  self.interrupted();self.task.pop('request_id');self.binding['server_answer_id']='local_cid_answer'
  self.raw['message'].update(serverId='local_cid_answer',serverIndex=1,serverPairId='local_cid_question')
  self.raw['question']['serverId']='local_cid_question'
  self.raw['entities']=[{'type':'TEXT','textEntity':{'text':'回答拉取失败，正在重试'}}]
  self.raw['render_snapshot']={'h':{'traceId':'trace'}}
  self.assertTrue(original_pair_matches(self.binding,self.task,self.raw))
  self.raw['entities'][0]['textEntity']['text']='正常回答'
  self.assertFalse(original_pair_matches(self.binding,self.task,self.raw))

 def test_memory_title_requires_original_first_pair_trace_and_unique_cid_title(self):
  entries=self.interrupted()
  with patch('history_refresh.databases',return_value=[self.p]):
   self.assertEqual(memory_history(self.binding,self.task,self.raw,entries)['conversation_id'],'cid')
   for bad in ([{'conversation_id':'other','title':'原会话'}],entries+[{'conversation_id':'cid','title':'不同标题'}],
       entries+[{'conversation_id':'other','title':'原会话'}]):
    self.assertIsNone(memory_history(self.binding,self.task,self.raw,bad))
   self.assertIsNone(memory_history(self.binding,{**self.task,'request_id':'other'},self.raw,entries))
   self.raw['question']['serverIndex']=3
   self.assertIsNone(memory_history(self.binding,self.task,self.raw,entries))

 def test_interrupted_memory_reload_without_persisted_answer_is_bounded_and_never_sends(self):
  entries=self.interrupted()
  (self.root/'task.native.json').write_text(json.dumps(self.raw));(self.root/'task.binding.json').write_text(json.dumps(self.binding))
  a=Mock();a.device.return_value.count=1
  a.device.dump_hierarchy.return_value='<hierarchy><node text="测试问题"/><node text="原会话"/><node text="另一会话"/></hierarchy>'
  history=Mock(return_value=entries);observed={'reason':'native_answer_interrupted'}
  with patch('history_refresh.databases',return_value=[self.p]),patch('history_refresh.stored_history',return_value=None):
   result=refresh_original(self.root,self.task,observed,a,Mock(),Mock(),history_entries=history,clock=lambda:1000,sleep=Mock())
   self.assertEqual(result['phase'],'reloading_original_history');self.assertEqual(a.tap.call_count,4)
   self.assertFalse(a.send.called)
   self.assertIsNone(refresh_original(self.root,self.task,observed,a,Mock(),Mock(),history_entries=history,clock=lambda:1001))
   self.assertEqual(history.call_count,1)

 def test_user_pause_or_composer_text_prevents_interrupted_navigation(self):
  entries=self.interrupted()
  (self.root/'task.native.json').write_text(json.dumps(self.raw));(self.root/'task.binding.json').write_text(json.dumps(self.binding))
  a=Mock();history=Mock(return_value=entries);observed={'reason':'native_answer_interrupted'}
  self.assertIsNone(refresh_original(self.root,self.task,observed,a,Mock(),Mock(),paused=True,history_entries=history,clock=lambda:1000))
  history.assert_not_called()
  a.device.dump_hierarchy.return_value='<hierarchy><node text="测试问题"/><node class="android.widget.EditText" text="用户草稿"/></hierarchy>'
  with patch('history_refresh.databases',return_value=[self.p]):
   self.assertIsNone(refresh_original(self.root,self.task,observed,a,Mock(),Mock(),history_entries=history,clock=lambda:1000))
  a.tap.assert_not_called()

 def test_interrupted_falls_back_to_verified_drawer_when_legacy_stores_missing(self):
  self.interrupted()
  (self.root/'task.native.json').write_text(json.dumps(self.raw));(self.root/'task.binding.json').write_text(json.dumps(self.binding))
  a=Mock();a.device.return_value.count=1
  a.device.dump_hierarchy.return_value='<hierarchy><node text="测试问题"/><node text="原会话"/><node text="另一会话"/></hierarchy>'
  proof={'title':'原会话','other_titles':['另一会话'],'conversation_id':'cid','request_id':'trace'}
  with patch('history_refresh.stored_history',return_value=None),patch('history_refresh.memory_history',return_value=None),patch('history_refresh.stored_drawer_proof',return_value=proof) as drawer:
   result=refresh_original(self.root,self.task,{'reason':'native_answer_interrupted'},a,Mock(),Mock(),history_entries=Mock(),clock=lambda:1000,sleep=Mock())
   self.assertEqual(result['phase'],'reloading_original_history');self.assertEqual(a.tap.call_count,4);a.send.assert_not_called();drawer.assert_called_once()

 def test_process_restart_home_restores_only_proven_original_history_without_send(self):
  entries=self.interrupted()
  (self.root/'task.native.json').write_text(json.dumps(self.raw));(self.root/'task.binding.json').write_text(json.dumps(self.binding))
  a=Mock();a.device.app_current.return_value={'package':'com.tencent.hunyuan.app.chat'};a.device.return_value.count=1
  a.device.dump_hierarchy.return_value='<hierarchy><node text="Hi，测试"/><node class="android.widget.EditText" text="发消息或按住说话..."/></hierarchy>'
  with patch('history_refresh.databases',return_value=[self.p]):
   result=restore_after_exit(self.root,self.task,a,Mock(),Mock(),lambda:entries,clock=lambda:1000,sleep=Mock())
  self.assertEqual(result['phase'],'reloading_original_history');self.assertEqual(a.tap.call_count,2);a.send.assert_not_called()
  self.assertIsNone(restore_after_exit(self.root,self.task,a,Mock(),Mock(),Mock(),clock=lambda:1001))

 def test_process_restart_wrong_trace_pause_or_user_draft_never_navigates(self):
  self.interrupted();(self.root/'task.native.json').write_text(json.dumps(self.raw));(self.root/'task.binding.json').write_text(json.dumps(self.binding))
  a=Mock();a.device.app_current.return_value={'package':'com.tencent.hunyuan.app.chat'}
  a.device.dump_hierarchy.return_value='<hierarchy><node text="Hi，测试"/><node class="android.widget.EditText" text="用户草稿"/></hierarchy>'
  for kwargs in ({'paused':True},{'stopping':True},{}):self.assertIsNone(restore_after_exit(self.root,self.task,a,Mock(),Mock(),Mock(),clock=lambda:1000,**kwargs))
  self.task['request_id']='different';self.assertIsNone(restore_after_exit(self.root,self.task,a,Mock(),Mock(),Mock(),clock=lambda:1000));a.tap.assert_not_called()
 def test_new_history_store_uses_cid_and_visible_order_even_when_old_title_repeats(self):
  self.interrupted();rows=[{'id':'cid','title':'原会话'},{'id':'other','title':'另一会话'},{'id':'third','title':'第三条'},{'id':'older','title':'原会话'}]
  xml='<hierarchy><node text="原会话"/><node text="另一会话"/><node text="第三条"/></hierarchy>'
  with patch('history_refresh.history_stores',return_value=[rows]):
   self.assertEqual(stored_drawer_proof(self.binding,self.task,self.raw,xml)['visible_history_ids'],['cid','other','third'])
   self.assertIsNone(stored_drawer_proof(self.binding,self.task,self.raw,xml.replace('另一会话','不相关会话')))
   self.assertIsNone(stored_drawer_proof({**self.binding,'conversation_id':'older'},self.task,self.raw,xml))

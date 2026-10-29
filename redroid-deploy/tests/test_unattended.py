
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[1]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import os
import time
import subprocess
import sys
from unittest.mock import Mock,patch
from types import SimpleNamespace

from unattended_core import DataError, Queue, lookup, is_transient_error

class FreshChatTests(unittest.TestCase):
    def test_empty_new_chat_without_create_button_is_recognized(self):
        from unattended_worker import is_blank_landing
        xml='<hierarchy><node text="为你推荐"/><node resource-id="com.larus.nova:id/input_text"/><node resource-id="com.larus.nova:id/back_icon" content-desc="返回"/></hierarchy>'
        self.assertTrue(is_blank_landing(xml))
        self.assertFalse(is_blank_landing(xml.replace('为你推荐','采集任务编号：old')))
        self.assertFalse(is_blank_landing('<hierarchy><node text="为你推荐"/></hierarchy>'))

    def test_notification_dialog_is_dismissed_before_chat(self):
        from unattended_worker import Android
        android=Android.__new__(Android)
        message=Mock()
        message.exists=True
        message.get_text.return_value='Allow 豆包 to send you notifications?'
        deny=Mock()
        def select(**kwargs):
            return message if kwargs['resourceId'].endswith('permission_message') else deny
        android.device=Mock(side_effect=select)
        android.tap=Mock(side_effect=lambda _: setattr(message,'exists',False))
        create=Mock(exists=True)
        self.assertTrue(android.wait_for_chat(create,1))
        android.tap.assert_called_once_with(deny)

    def test_other_permission_is_not_automatically_changed(self):
        from unattended_worker import Android
        android=Android.__new__(Android)
        android.device=Mock()
        android.device.return_value.exists=True
        android.device.return_value.get_text.return_value='Allow 豆包 to use your camera?'
        android.device.dump_hierarchy.return_value='<hierarchy/>'
        android.tap=Mock()
        self.assertFalse(android.wait_for_chat(Mock(exists=False),.01))
        android.tap.assert_not_called()

    def test_repeated_notification_dialog_uses_second_denial_variant(self):
        from unattended_worker import Android
        android=Android.__new__(Android)
        message=Mock(exists=True);message.get_text.return_value='Allow 豆包 to send you notifications?'
        ordinary=Mock(exists=False);permanent=Mock(exists=True)
        selectors={'permission_message':message,'permission_deny_button':ordinary,
                   'permission_deny_and_dont_ask_again_button':permanent}
        android.device=lambda **kwargs:selectors[kwargs['resourceId'].rsplit('/',1)[1]]
        android.tap=Mock()
        self.assertTrue(android.dismiss_notification_prompt())
        android.tap.assert_called_once_with(permanent)

    def test_old_failed_chat_with_input_is_rejected(self):
        from unattended_worker import assert_fresh_chat
        with self.assertRaisesRegex(DataError, '新对话创建未成功'):
            assert_fresh_chat('<hierarchy><node text="旧问题（采集任务编号：old）"/><node resource-id="com.larus.nova:id/input_text" text="新问题"/></hierarchy>')

    def test_new_question_in_edit_box_is_allowed(self):
        from unattended_worker import assert_fresh_chat
        assert_fresh_chat('<hierarchy><node text="你好"/><node resource-id="com.larus.nova:id/input_text" text="新问题（采集任务编号：new）"/></hierarchy>')

    def test_duplicate_current_question_outside_edit_is_rejected(self):
        from unattended_worker import assert_fresh_chat
        with self.assertRaises(DataError):
            assert_fresh_chat('<hierarchy><node text="新问题（采集任务编号：new）"/><node resource-id="com.larus.nova:id/input_text" text="新问题（采集任务编号：new）"/></hierarchy>')


class ReliabilityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.queue=Queue(self.root/'queue.db')
        self.queue.enqueue('test-batch',['测试联网问题'],True)
        self.task=self.queue.next_task()
        self.chat=self.root/'chat.db'
        self.db=sqlite3.connect(self.chat)
        self.db.execute('create table im_message(local_message_id text,conversation_id text,local_index integer,user_type integer,content text,fts_content text)')
        self.blocks=[{'is_finish':True,'content':{'search_query_result_block':{'queries':['测试'], 'results':[{'text_card':{'index':1,'title':'测试来源','url':'https://example.com/source','doc_id':'doc-1'}}]}},'meta_info':[]},
                     {'is_finish':True,'content':{'text_block':{'text':'**完整回答**'}},'meta_info':[{'info':json.dumps({'url':'https://example.com/source','doc_id':'doc-1','pos':[3]})}]}]

    def tearDown(self):
        self.db.close()
        self.queue.db.close()
        self.temp.cleanup()

    def add(self,identity,role,index,wire=None,blocks=None,conversation='c1'):
        self.db.execute('insert into im_message values(?,?,?,?,?,?)',(identity,conversation,index,role,json.dumps(blocks or self.blocks),wire or '完整回答'))
        self.db.commit()

    def complete_pair(self):
        self.add('request-1',1,2000,self.task['wire_question'])
        self.add('answer-1',2,3000)
        return lookup([self.chat],self.task)

    def test_enqueue_same_batch_is_idempotent(self):
        self.queue.enqueue('test-batch',['测试联网问题'],True)
        self.assertEqual(self.queue.summary(),{'pending':1})

    def test_unindexed_request_is_waiting_not_absent(self):
        blocks=[{'content':{'text_block':{'text':self.task['wire_question']}},'is_finish':False}]
        self.add('request-1',1,2000,blocks=blocks)
        self.db.execute("update im_message set fts_content=null where local_message_id='request-1'")
        self.db.commit()
        result=lookup([self.chat],self.task)
        self.assertEqual(result['status'],'waiting')
        self.assertEqual(result['request_id'],'request-1')
        self.add('answer-1',2,3000)
        self.assertEqual(lookup([self.chat],self.task)['status'],'complete')

    def test_cannot_change_existing_batch(self):
        with self.assertRaises(DataError):
            self.queue.enqueue('test-batch',['不同问题'],True)

    def test_intent_survives_process_restart(self):
        self.queue.prepare(self.task['task_id'])
        self.queue.db.close()
        self.queue=Queue(self.root/'queue.db')
        self.assertEqual(self.queue.next_task()['state'],'prepared')
        with self.assertRaises(DataError):
            self.queue.prepare(self.task['task_id'])

    def test_uncertain_send_is_not_returned_as_pending(self):
        self.queue.prepare(self.task['task_id'])
        self.assertEqual(lookup([self.chat],self.task)['status'],'absent')
        with self.assertRaises(DataError):
            self.queue.retry_preparation(self.task['task_id'],'unknown delivery')

    def test_crash_after_send_recovers_by_request_id(self):
        self.queue.prepare(self.task['task_id'])
        result=self.complete_pair()
        self.queue.complete(self.task['task_id'],result)
        self.assertEqual(self.queue.summary(),{'completed':1})
        self.assertEqual(result['request_id'],'request-1')

    def test_completed_task_is_not_dispatched_again(self):
        self.queue.prepare(self.task['task_id'])
        self.queue.complete(self.task['task_id'],self.complete_pair())
        self.assertIsNone(self.queue.next_task())

    def test_unrelated_old_answer_is_excluded(self):
        self.add('old-request',1,1000,'旧问题',conversation='old')
        self.add('old-answer',2,3000,conversation='old')
        self.add('new-request',1,2000,self.task['wire_question'])
        self.assertEqual(lookup([self.chat],self.task)['status'],'waiting')

    def test_role_is_required(self):
        self.add('answer-echo',2,1000,self.task['wire_question'])
        self.assertEqual(lookup([self.chat],self.task)['status'],'absent')

    def test_partial_stream_does_not_complete(self):
        self.blocks[-1]['is_finish']=False
        self.assertEqual(self.complete_pair()['status'],'waiting')

    def test_duplicate_request_is_rejected(self):
        self.add('r1',1,1000,self.task['wire_question'])
        self.add('r2',1,1000,self.task['wire_question'],conversation='other')
        with self.assertRaises(DataError):
            lookup([self.chat],self.task)

    def test_regenerated_answers_are_not_guessed(self):
        self.complete_pair()
        self.add('regeneration',2,4000)
        with self.assertRaises(DataError):
            lookup([self.chat],self.task)

    def test_answer_after_next_user_message_is_excluded(self):
        self.add('r1',1,1000,self.task['wire_question'])
        self.add('r2',1,2000,'后续问题')
        self.add('later-answer',2,3000)
        self.assertEqual(lookup([self.chat],self.task)['status'],'waiting')

    def test_wrong_task_result_cannot_commit(self):
        self.queue.prepare(self.task['task_id'])
        result=self.complete_pair()
        result['task_id']='someone-else'
        with self.assertRaises(DataError):
            self.queue.complete(self.task['task_id'],result)

    def test_source_requirement_is_enforced(self):
        self.queue.prepare(self.task['task_id'])
        result=self.complete_pair()
        result['sources']=[]
        with self.assertRaises(DataError):
            self.queue.complete(self.task['task_id'],result)

    def transient_result(self):
        result=self.complete_pair()
        result.update(body_markdown='出了点问题，请稍后重试。',sources=[],citations=[],native_request_confirmed=True)
        return result

    def test_confirmed_error_is_archived_and_retry_has_unique_wire(self):
        self.queue.prepare(self.task['task_id'],protocol='phase-v2');self.queue.click_attempt(self.task['task_id'])
        result=self.transient_result()
        delay=self.queue.schedule_transient_retry(self.task['task_id'],result)
        retry=self.queue.next_task()
        self.assertEqual(delay,90)
        self.assertGreater(retry['not_before'],time.time()+80)
        self.assertNotEqual(retry['wire_question'],self.task['wire_question'])
        self.assertEqual(retry['task_id'],self.task['task_id'])
        self.assertEqual(lookup([self.chat],retry)['status'],'absent')
        archived=self.queue.db.execute('select result_json from failed_attempts').fetchone()[0]
        self.assertEqual(json.loads(archived),result)
        self.queue.prepare(retry['task_id'],protocol='phase-v2');self.queue.click_attempt(retry['task_id'])
        with self.assertRaises(DataError):self.queue.click_attempt(retry['task_id'])
        self.assertEqual(self.queue.db.execute("select count(*) from events where event='send_click_intent_committed'").fetchone()[0],2)

    def test_unconfirmed_or_normal_sourceless_answer_cannot_retry(self):
        self.queue.prepare(self.task['task_id'],protocol='phase-v2')
        result=self.transient_result()
        result['native_request_confirmed']=False
        with self.assertRaises(DataError):self.queue.schedule_transient_retry(self.task['task_id'],result)
        result.update(native_request_confirmed=True,body_markdown='一个普通推荐回答')
        with self.assertRaises(DataError):self.queue.schedule_transient_retry(self.task['task_id'],result)
        self.assertEqual(self.queue.summary(),{'prepared':1})

    def test_transient_retries_are_bounded_and_backoff_survives_restart(self):
        self.queue.prepare(self.task['task_id'],protocol='phase-v2')
        result=self.transient_result()
        for attempt,delay in enumerate((90,180)):
            task=self.queue.next_task();result['wire_question']=task['wire_question']
            self.assertEqual(self.queue.schedule_transient_retry(task['task_id'],result),delay)
            self.queue.db.close();self.queue=Queue(self.root/'queue.db')
            task=self.queue.next_task()
            self.assertEqual(task['capture_retries'],attempt+1)
            self.assertGreater(task['not_before'],time.time()+delay-5)
            self.queue.prepare(task['task_id'],protocol='phase-v2')
        result['wire_question']=self.queue.next_task()['wire_question']
        with self.assertRaisesRegex(DataError,'retry limit'):self.queue.schedule_transient_retry(self.task['task_id'],result)

    def test_old_database_schema_migrates_without_resetting_history(self):
        path=self.root/'legacy.sqlite'
        with sqlite3.connect(path) as db:
            db.execute('create table tasks(task_id text primary key,batch text,ordinal integer,question text,wire_question text,require_sources integer,state text,attempts integer,prepared_at real,request_id text,answer_id text,result_json text,error text)')
            db.execute("insert into tasks values('old','legacy',1,'question','old-wire',1,'completed',0,1,'request','answer','{}',null)")
        db.close()
        migrated=Queue(path)
        self.assertEqual(migrated.summary(),{'completed':1})
        self.assertEqual(migrated.db.execute('select base_wire_question from tasks').fetchone()[0],'old-wire')
        migrated.db.close()

    def test_invalid_url_cannot_be_success(self):
        self.queue.prepare(self.task['task_id'])
        result=self.complete_pair()
        result['sources'][0]['url']='not-a-link'
        with self.assertRaises(DataError):
            self.queue.complete(self.task['task_id'],result)

    def test_citation_to_missing_source_is_rejected(self):
        self.queue.prepare(self.task['task_id'])
        result=self.complete_pair()
        result['citations'][0]['doc_id']='missing-source'
        with self.assertRaises(DataError):
            self.queue.complete(self.task['task_id'],result)

    def test_invalid_citation_url_is_rejected(self):
        self.queue.prepare(self.task['task_id'])
        result=self.complete_pair()
        result['citations'][0]['url']='javascript:invalid'
        with self.assertRaises(DataError):
            self.queue.complete(self.task['task_id'],result)

    def test_schema_change_is_visible(self):
        other=self.root/'bad-schema.db'
        with sqlite3.connect(other) as db:
            db.execute('create table im_message(content text)')
        db.close()
        with self.assertRaises(DataError):
            lookup([other],self.task)

    def test_unknown_block_does_not_silently_disappear(self):
        self.blocks.append({'is_finish':True,'content':{'unrecognized_table':{}}})
        with self.assertRaises(DataError):
            self.complete_pair()

    def test_observed_empty_pc_metadata_is_allowed(self):
        for block in self.blocks:
            block['content']['pc_event_block']=''
        self.assertEqual(self.complete_pair()['status'],'complete')

    def test_pre_send_retries_have_a_circuit_breaker(self):
        for _ in range(3):
            self.queue.retry_preparation(self.task['task_id'],'native bridge crash')
        self.assertEqual(self.queue.summary(),{'needs_attention':1})

    def test_restart_before_click_can_finish_original_send(self):
        self.queue.prepare(self.task['task_id'], protocol='phase-v2')
        reopened = Queue(self.queue.path)
        self.assertTrue(reopened.may_finish_unsent(self.task['task_id']))
        reopened.click_attempt(self.task['task_id'])
        self.assertFalse(self.queue.may_finish_unsent(self.task['task_id']))
        with self.assertRaises(DataError):
            reopened.click_attempt(self.task['task_id'])
        reopened.db.close()

    def test_legacy_intent_is_not_assumed_unsent(self):
        self.queue.prepare(self.task['task_id'])
        self.assertFalse(self.queue.may_finish_unsent(self.task['task_id']))

    def test_click_intent_without_confirmation_cannot_retry(self):
        self.queue.prepare(self.task['task_id'], protocol='phase-v2')
        self.queue.click_attempt(self.task['task_id'])
        with self.assertRaises(DataError):
            self.queue.retry_preparation(self.task['task_id'], 'interrupted after click intent')

    def test_unsent_recovery_preserves_prepared_state(self):
        self.queue.prepare(self.task['task_id'], protocol='phase-v2')
        self.queue.retry_preparation(self.task['task_id'], 'temporary UI failure')
        self.assertEqual(self.queue.summary(), {'prepared':1})
        self.assertTrue(self.queue.may_finish_unsent(self.task['task_id']))

    @unittest.skipUnless(os.name=='posix','Linux export locking')
    def test_export_includes_the_original_question(self):
        from unattended_worker import export
        self.queue.prepare(self.task['task_id'])
        self.queue.complete(self.task['task_id'],self.complete_pair())
        self.assertEqual(export(self.queue,self.root),1)
        result=json.loads((self.root/'answers.json').read_text())
        self.assertEqual(result[0]['question'],self.task['question'])

    @unittest.skipUnless(os.name=='posix','Linux export locking')
    def test_multiple_export_processes_publish_valid_results(self):
        self.queue.prepare(self.task['task_id'])
        self.queue.complete(self.task['task_id'],self.complete_pair())
        code='from pathlib import Path; from unattended_core import Queue; from unattended_worker import export; import sys; export(Queue(Path(sys.argv[1])/"queue.db"),Path(sys.argv[1]))'
        processes=[subprocess.Popen([sys.executable,'-c',code,str(self.root)],cwd=_GEO_TOOL_ROOT,
                   stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(4)]
        for process in processes:
            _,errors=process.communicate(timeout=10)
            self.assertEqual(process.returncode,0,errors.decode())
        results=json.loads((self.root/'answers.json').read_text())
        self.assertEqual([r['task_id'] for r in results],[self.task['task_id']])

    def test_temporary_input_disappearance_retries_before_click_only(self):
        from unattended_worker import Android
        from uiautomator2.exceptions import UiObjectNotFoundError
        android=Android.__new__(Android)
        android.device=Mock()
        android.device.dump_hierarchy.return_value='<hierarchy/>'
        edit=android.device.return_value
        edit.info={'bounds':{'left':0,'top':0,'right':10,'bottom':10},'enabled':True}
        edit.wait.return_value=True
        edit.set_text.side_effect=[UiObjectNotFoundError('temporary input transition'),None]
        edit.get_text.return_value=self.task['wire_question']
        android.tap=Mock()
        commit=Mock()
        android.send(self.task['wire_question'],commit)
        self.assertEqual(edit.set_text.call_count,2)
        commit.assert_called_once()
        android.tap.assert_called_once()

    def test_send_click_failure_is_never_retried(self):
        from unattended_worker import Android
        from uiautomator2.exceptions import UiObjectNotFoundError
        android=Android.__new__(Android)
        android.device=Mock()
        android.device.dump_hierarchy.return_value='<hierarchy/>'
        android.device.return_value.get_text.return_value=self.task['wire_question']
        android.device.return_value.info={'bounds':{'left':0,'top':0,'right':10,'bottom':10},'enabled':True}
        android.device.return_value.wait.return_value=True
        android.tap=Mock(side_effect=UiObjectNotFoundError('send outcome uncertain'))
        commit=Mock()
        with self.assertRaises(UiObjectNotFoundError):
            android.send(self.task['wire_question'],commit)
        commit.assert_called_once()
        android.tap.assert_called_once()

    def test_missing_send_button_does_not_commit_click_intent(self):
        from unattended_worker import Android
        android=Android.__new__(Android);android.device=Mock()
        android.device.dump_hierarchy.return_value='<hierarchy/>'
        android.device.return_value.get_text.return_value=self.task['wire_question']
        android.device.return_value.wait.return_value=False
        android.tap=Mock();commit=Mock()
        with self.assertRaisesRegex(DataError,'no click dispatched'):android.send(self.task['wire_question'],commit)
        commit.assert_not_called();android.tap.assert_not_called()

    @unittest.skipUnless(os.name=='posix','Linux device and export locks')
    def test_maintenance_pause_finishes_inflight_and_does_not_dispatch_next(self):
        from unattended_worker import run
        self.queue.enqueue('another-batch',['下一题'],True)
        self.queue.prepare(self.task['task_id'],protocol='phase-v2')
        self.complete_pair()
        (self.root/'maintenance_pause.json').write_text('{}')
        args=SimpleNamespace(container='test-pause-'+self.task['task_id'],once=True,continue_on_task_error=False)
        with patch('unattended_worker.databases',return_value=[self.chat]),patch('unattended_worker.Android') as android:
            self.assertEqual(run(args,self.queue,self.root),0)
            android.assert_not_called()
        self.assertEqual(self.queue.summary(),{'completed':1,'pending':1})
        self.assertEqual(json.loads((self.root/'health.json').read_text())['status'],'maintenance_paused')

    @unittest.skipUnless(os.name=='posix','Linux wall-clock deadline')
    def test_hung_android_operation_has_a_deadline(self):
        from unattended_worker import deadline
        with self.assertRaises(TimeoutError):
            with deadline(.05):
                time.sleep(1)


if __name__=='__main__':
    unittest.main(verbosity=2)

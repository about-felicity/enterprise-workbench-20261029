import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
import os
import time
import subprocess
import sys
from unittest.mock import Mock

from unattended_core import DataError, Queue, lookup


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
        processes=[subprocess.Popen([sys.executable,'-c',code,str(self.root)],cwd=Path(__file__).parent,
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
        edit=android.device.return_value
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
        android.device.return_value.get_text.return_value=self.task['wire_question']
        android.tap=Mock(side_effect=UiObjectNotFoundError('send outcome uncertain'))
        commit=Mock()
        with self.assertRaises(UiObjectNotFoundError):
            android.send(self.task['wire_question'],commit)
        commit.assert_called_once()
        android.tap.assert_called_once()

    @unittest.skipUnless(os.name=='posix','Linux wall-clock deadline')
    def test_hung_android_operation_has_a_deadline(self):
        from unattended_worker import deadline
        with self.assertRaises(TimeoutError):
            with deadline(.05):
                time.sleep(1)


if __name__=='__main__':
    unittest.main(verbosity=2)

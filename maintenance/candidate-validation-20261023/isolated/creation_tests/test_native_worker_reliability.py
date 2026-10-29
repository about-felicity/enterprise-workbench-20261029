"""Linux worker fault injection with real durable SQLite; no device/network."""
import contextlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch

from question_only_core import Queue
from runtime_reliability import CompletionFence

spec=importlib.util.spec_from_file_location('candidate_worker',Path(os.environ.get('GEO_TEST_WORKER','/tmp/geo-reliability-stage/question_only_worker.py')))
worker=importlib.util.module_from_spec(spec);spec.loader.exec_module(worker)


class NativeWorkerTests(unittest.TestCase):
    def test_yuanbao_cold_process_opens_before_native_baseline_and_single_send(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'batches/fixture';root.mkdir(parents=True)
            q=Queue(root/'tasks.sqlite');q.enqueue('fixture',['问题'],True);task=q.next_task();q.db.close()
            result={'status':'complete','task_id':task['task_id'],'wire_question':'问题','finished':True,
                    'native_request_confirmed':True,'request_id':'r','answer_id':'a','conversation_id':'c',
                    'body_markdown':'完整回答','sources':[{'title':'来源','url':'https://a.test'}]}
            reader=Mock();reader.lookup.side_effect=[{'status':'absent'},result,result]
            android=Mock();opened=[]
            android.ensure_open.side_effect=lambda:opened.append(True)
            def baseline(_):
                if not opened:raise RuntimeError('App pid missing')
            reader.before_new_chat.side_effect=baseline
            android.send.side_effect=lambda question,commit:commit()
            delivery=Mock();delivery.sync.side_effect=lambda queue:{'captured':queue.summary().get('completed',0),'geo_processed':queue.summary().get('completed',0),'delivery_errors':[]}
            with patch.object(worker,'yuanbao_reader',return_value=reader),patch.object(worker,'Delivery',return_value=delivery), \
                 patch.object(worker,'make_android',return_value=android),patch.object(worker,'native_auth_required',return_value=False), \
                 patch.object(worker,'CompletionFence',side_effect=lambda:CompletionFence(seconds=0)),patch.object(worker.time,'sleep'),patch.object(worker,'STOP',False):
                self.assertEqual(worker.run_locked({**self.config(),'model':'yuanbao'},root,0),0)
            android.ensure_open.assert_called_once();android.send.assert_called_once()

    def config(self):return {'batch':'fixture','questions':['问题'],'rounds':1,'interval':45,
                             'model':'doubao1','container':'fixture-device','serial':'fixture'}

    def test_video_terminal_is_audited_without_text_success_or_model_resend(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'batches/fixture';root.mkdir(parents=True)
            q=Queue(root/'tasks.sqlite');q.enqueue('fixture',['问题'],True);task=q.next_task();q.db.close()
            result={'status':'nontext_complete','native_answer_kind':'video_only','task_id':task['task_id'],
                'wire_question':'问题','finished':True,'native_request_confirmed':True,'request_id':'r','answer_id':'a',
                'conversation_id':'c','body_markdown':'native-video-placeholder','sources':[],
                'first_user_turn':True,'prompt_protocol':'question-only-v1','text_body_present':False,
                'body_capture_complete':False,'rich_media_capture_complete':True,'rich_cards':[{'id':'card'}]}
            reader=Mock();reader.lookup.side_effect=[{'status':'absent'},result,result]
            android=Mock();android.send.side_effect=lambda question,commit:commit()
            delivery=Mock();delivery.sync.side_effect=lambda queue:{'captured':0,'geo_processed':0,'delivery_errors':[],
                'nontext_observations':queue.summary().get('completed_nontext',0),'nontext_processed':queue.summary().get('completed_nontext',0),'nontext_pending':0}
            with patch.object(worker,'yuanbao_reader',return_value=reader),patch.object(worker,'Delivery',return_value=delivery), \
                 patch.object(worker,'make_android',return_value=android),patch.object(worker,'CompletionFence',side_effect=lambda:CompletionFence(seconds=0)), \
                 patch.object(worker.time,'sleep'),patch.object(worker,'STOP',False):
                self.assertEqual(worker.run_locked({**self.config(),'model':'yuanbao'},root,0),0)
            android.send.assert_called_once()
            health=json.loads((root/'bridge_health.json').read_text())
            self.assertEqual(health['status'],'complete_with_unavailable')
            self.assertEqual((health['captured'],health['geo_processed'],health['unavailable'],health['nontext_processed']),(0,0,1,1))

    def test_single_click_two_consistent_complete_reads_then_delivery(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'batches/fixture';root.mkdir(parents=True)
            q=Queue(root/'tasks.sqlite');q.enqueue('fixture',['问题'],True);task=q.next_task();q.db.close()
            result={'status':'complete','task_id':task['task_id'],'wire_question':'问题','finished':True,
                    'native_request_confirmed':True,'request_id':'r','answer_id':'a','conversation_id':'c',
                    'body_markdown':'短。','sources':[{'title':'完整来源','url':'https://a.test'}]}
            reader=Mock();reader.lookup.side_effect=[{'status':'absent'},result,result]
            android=Mock();android.send.side_effect=lambda question,commit:commit()
            delivery=Mock();delivery.sync.side_effect=lambda queue:{'captured':queue.summary().get('completed',0),
                'geo_processed':queue.summary().get('completed',0),'delivery_errors':[]}
            with patch.object(worker,'DoubaoReader',return_value=reader),patch.object(worker,'DoubaoDelivery',return_value=delivery), \
                 patch.object(worker,'make_android',return_value=android),patch.object(worker,'CompletionFence',side_effect=lambda:CompletionFence(seconds=0)), \
                 patch.object(worker.time,'sleep'),patch.object(worker,'STOP',False):
                self.assertEqual(worker.run_locked(self.config(),root,0),0)
            android.send.assert_called_once();self.assertEqual(reader.lookup.call_count,3)
            q=Queue(root/'tasks.sqlite');self.assertEqual(q.summary(),{'completed':1})
            self.assertEqual(q.db.execute("select count(*) from events where event='send_click_intent_committed'").fetchone()[0],1)
            q.db.close()

    def test_more_than_five_read_failures_recovers_original_without_resending(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'batches/fixture';root.mkdir(parents=True)
            q=Queue(root/'tasks.sqlite');q.enqueue('fixture',['问题'],True);task=q.next_task()
            q.prepare(task['task_id'],protocol='phase-v2');q.click_attempt(task['task_id']);q.db.close()
            result={'status':'complete','task_id':task['task_id'],'wire_question':'问题','finished':True,
                    'native_request_confirmed':True,'request_id':'r','answer_id':'a','conversation_id':'c',
                    'body_markdown':'完整回答','sources':[{'title':'完整来源','url':'https://a.test'}]}
            reader=Mock();reader.lookup.side_effect=[TimeoutError('private detail')]*6+[result,result]
            android=Mock();delivery=Mock();delivery.sync.side_effect=lambda queue:{'captured':queue.summary().get('completed',0),'geo_processed':queue.summary().get('completed',0),'delivery_errors':[]}
            with patch.object(worker,'DoubaoReader',return_value=reader),patch.object(worker,'DoubaoDelivery',return_value=delivery), \
                 patch.object(worker,'make_android',return_value=android),patch.object(worker.time,'sleep'),patch.object(worker,'STOP',False), \
                 patch.object(worker,'CompletionFence',side_effect=lambda:CompletionFence(seconds=0)):
                self.assertEqual(worker.run_locked(self.config(),root,0),0)
            android.send.assert_not_called();self.assertEqual(reader.lookup.call_count,8)
            q=Queue(root/'tasks.sqlite');self.assertEqual(q.summary(),{'completed':1});q.db.close()
            health=json.loads((root/'bridge_health.json').read_text())
            self.assertNotIn('private detail',json.dumps(health))

    def test_confirmed_login_loss_stops_with_dedicated_exit_status(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'batches/fixture';root.mkdir(parents=True)
            delivery=Mock();delivery.sync.return_value={'captured':0,'geo_processed':0,'delivery_errors':[]}
            android=Mock()
            with patch.object(worker,'DoubaoReader'),patch.object(worker,'DoubaoDelivery',return_value=delivery), \
                 patch.object(worker,'make_android',return_value=android),patch.object(worker,'native_auth_required',return_value=True):
                self.assertEqual(worker.run_locked(self.config(),root,0),77)
            android.send.assert_not_called()
            self.assertEqual(json.loads((root/'bridge_health.json').read_text())['status'],'waiting_login')

    def test_response_after_old_900_second_deadline_is_still_completed_without_send(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'batches/fixture';root.mkdir(parents=True)
            q=Queue(root/'tasks.sqlite');q.enqueue('fixture',['问题'],True);task=q.next_task()
            q.prepare(task['task_id'],protocol='phase-v2');q.click_attempt(task['task_id'])
            with q.db:q.db.execute('update tasks set prepared_at=?',(worker.time.time()-1000,))
            q.db.close()
            result={'status':'complete','task_id':task['task_id'],'wire_question':'问题','finished':True,
                    'native_request_confirmed':True,'request_id':'r','answer_id':'a','conversation_id':'c',
                    'body_markdown':'完整回答','sources':[{'title':'来源','url':'https://a.test'}]}
            reader=Mock();reader.lookup.side_effect=[{'status':'waiting'},result,result]
            android=Mock();delivery=Mock();delivery.sync.side_effect=lambda queue:{'captured':queue.summary().get('completed',0),'geo_processed':queue.summary().get('completed',0),'delivery_errors':[]}
            with patch.object(worker,'DoubaoReader',return_value=reader),patch.object(worker,'DoubaoDelivery',return_value=delivery), \
                 patch.object(worker,'make_android',return_value=android),patch.object(worker.time,'sleep'),patch.object(worker,'STOP',False), \
                 patch.object(worker,'CompletionFence',side_effect=lambda:CompletionFence(seconds=0)):
                self.assertEqual(worker.run_locked(self.config(),root,0),0)
            android.send.assert_not_called()
            self.assertEqual(json.loads((root/'bridge_health.json').read_text())['tasks'],{'completed':1})

if __name__=='__main__':unittest.main()

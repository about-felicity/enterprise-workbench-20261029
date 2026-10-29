import json
import unittest
import tempfile
from pathlib import Path
from geo_batch_bridge import envelope, record_shutdown


class BridgeTests(unittest.TestCase):
    def task(self):
        return {'task_id':'id1','ordinal':22,'batch':'batch','question':'推荐一款护发精油',
                'result_json':json.dumps({'finished':True,'body_markdown':'完整正文\n第二段',
                    'sources':[{'index':1,'title':'文章','url':'https://example.org/a','doc_id':'D1'}],
                    'citations':[{'doc_id':'D1','pos':3}], 'search_queries':['问题'],
                    'conversation_id':'c1','request_id':'r1','answer_id':'a1'})}

    def test_delivery_preserves_text_sources_and_round(self):
        task=self.task()
        value=envelope(task,1791856800)
        self.assertEqual(value['payload']['answerText'],'完整正文\n第二段')
        self.assertEqual(value['payload']['items'][0]['doc_id'],'D1')
        self.assertEqual(value['payload']['citations'][0]['pos'],3)
        self.assertEqual(value['payload']['round'],2)
        self.assertEqual(value['payload']['question_index'],1)
        self.assertEqual(value['request_id'],envelope(task,1791856801)['request_id'])
        task['task_id']='id2'
        self.assertNotEqual(value['request_id'],envelope(task,1791856800)['request_id'])

    def test_missing_sources_rejected(self):
        task=self.task()
        result=json.loads(task['result_json'])
        result['sources']=[]
        task['result_json']=json.dumps(result)
        with self.assertRaises(ValueError):envelope(task,1791856800)

    def test_shutdown_invalidates_running_snapshot_preserves_progress(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'bridge_health.json').write_text(json.dumps({'status':'running','tasks':{'prepared':1},'captured':3,'geo_processed':2}))
            record_shutdown(root,-15)
            health=json.loads((root/'bridge_health.json').read_text())
            self.assertEqual(health['status'],'stopped')
            self.assertEqual(health['geo_processed'],2)
            self.assertEqual(health['worker_exit'],-15)
            self.assertIsNone(health['heartbeat_expires_at'])
            record_shutdown(root,reason='systemd_stop:success')
            self.assertEqual(json.loads((root/'bridge_health.json').read_text())['worker_exit'],-15)

    def test_shutdown_preserves_completion_and_attention(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for status,tasks in [('complete',{'completed':105}),('needs_attention',{'needs_attention':1})]:
                (root/'bridge_health.json').write_text(json.dumps({'status':status,'tasks':tasks}))
                record_shutdown(root,0)
                self.assertEqual(json.loads((root/'bridge_health.json').read_text())['status'],status)

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'geo-source-card-collectors'))
import baidu_body_delivery as delivery


class BaiduBodyTests(unittest.TestCase):
    def test_body_delivery_is_visible_without_relabeling_sources_as_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            delivery.atomic_json(root/'body-only/health.json',
                                 {'observations':10,'processed':10,'unique_processed':2,'errors':[]})
            value=delivery.merge_health({'status':'complete_with_unavailable','captured':5,'processed':5,
                'unique_processed':1,'duplicates':4,'unavailable':10,'progress':{'phase':'complete_with_unavailable'}},root)
            self.assertEqual((value['captured'],value['processed'],value['unique_processed']),(15,15,3))
            self.assertEqual(value['source_backed_processed'],5)
            self.assertEqual(value['status'],'complete')
            self.assertEqual(value['progress']['phase'],'complete')
            self.assertEqual(value['unavailable'],0)

    def setUp(self):
        self.config = {'model': 'baidu_ai', 'device': 'baidu-test', 'rounds': 5}
        self.value = {'availability': 'body_only', 'capture_mode': 'baidu_search_ai',
                      'card_available': True, 'body_capture_complete': True,
                      'source_capture_complete': False, 'source_exposure': 'not_publicly_exposed',
                      'source_exposure_evidence': {'card_present': True, 'declared_count': 0, 'drawer_opened': False},
                      'body': '卡片完整正文', 'sources': [], 'expected_source_count': None,
                      'fresh_search': True, 'question': '测试', 'verified_question': '测试',
                      'url': 'https://www.baidu.com/s?wd=%E6%B5%8B%E8%AF%95', 'captured_at': '2026-10-16T10:00:00+08:00'}
        self.row = {'ordinal': 0, 'round': 1, 'task_id': 'task', 'batch': 'test', 'finished': 1,
                    'state': 'completed', 'result': json.dumps(self.value)}

    def test_gate_rejects_incomplete_prose_or_uncollected_sources(self):
        for change in ({'body_capture_complete': False}, {'verified_question': '别的问题'},
                       {'fresh_search': False}, {'source_capture_complete': True},
                       {'expected_source_count': 2}, {'body': ''}, {'url': 'https://wenxin.baidu.com/'}):
            with self.assertRaises(ValueError):
                delivery.envelope(self.row, {**self.value, **change}, self.config)
        bad = copy.deepcopy(self.value)
        bad['source_exposure_evidence']['drawer_opened'] = True
        with self.assertRaises(ValueError):
            delivery.envelope(self.row, bad, self.config)

    def test_receipt_requires_stored_body_and_honest_incomplete_sources(self):
        item = delivery.envelope(self.row, self.value, self.config)
        self.assertEqual(item['record']['capture_result'], self.value)
        reply = {'request_id': item['request_id'], 'model': 'wenxin', 'source_device': self.config['device'],
                 'stored_run_id': 'stored', 'analysis': {'answer_present': True, 'answer_length': 6,
                 'body_capture_complete': True, 'source_capture_complete': False, 'source_count': 0, 'sources': []}}
        delivery.verify_receipt(reply, item)
        for key, value in [('source_capture_complete', True), ('quarantined', True), ('answer_length', 1)]:
            bad = copy.deepcopy(reply)
            bad['analysis'][key] = value
            with self.assertRaises(ValueError):
                delivery.verify_receipt(bad, item)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            delivery.atomic_json(root / 'runtime/lan_result_receiver.json', {'port': 8791, 'token': 'test'})
            runner = delivery.Delivery(root / 'lane', self.config, root)
            runner.session = Mock()
            runner.session.get.return_value.json.return_value = {'status': 'queued'}
            runner.session.post.return_value.json.return_value = {'ok': True, 'request_id': item['request_id']}
            self.assertEqual(runner.sync([self.row])['pending_delivery'], 1)
            self.assertEqual(runner.session.post.call_count, 1)
            delivery.atomic_json(runner.root / 'receipts' / (item['request_id'] + '.json'), reply)
            runner.session.post.reset_mock()
            self.assertEqual(runner.sync([self.row])['processed'], 1)
            runner.session.post.assert_not_called()


if __name__ == '__main__':
    unittest.main()

import concurrent.futures
import importlib.util
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[2] / 'server-source/monitor_core/source_activity_index.py'
spec = importlib.util.spec_from_file_location('source_activity_index', SOURCE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ActivityIndexTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'index.json'

    def tearDown(self):
        self.temp.cleanup()

    def write(self, value):
        self.path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8-sig')

    def test_chunk_boundaries_and_exact_label_semantics(self):
        self.write({'version': 1e23, 'entries': {
            'https://测试/\\"': {'status': 'ok', 'own_product_mentions': ['产品'], 'excerpt': '汉字\\"{}' * 200},
            'empty': {'status': 'ok', 'own_product_mentions': []},
            'legacy': {'status': 'ok'}, 'failed': {'status': 'timeout'},
            'bad-label': {'status': 'ok', 'own_product_mentions': 'not a list'},
            'bad-entry': None}, 'after': [True, None, {'nested': '}"'}]})
        expected = {'https://测试/\\"': {'status': 'ok', 'own_product_mentions': [True]},
                    'empty': {'status': 'ok', 'own_product_mentions': []},
                    'legacy': {'status': 'ok'}, 'failed': {'status': 'timeout'},
                    'bad-label': {'status': 'ok'}}
        for chunk in [1, 2, 3, 7, 64, 65536]:
            with self.subTest(chunk=chunk):
                self.assertEqual(module.read_activity_entries(self.path, chunk_size=chunk), expected)

    def test_concurrent_cold_load_is_single_flight(self):
        self.write({'entries': {'a': {'status': 'ok'}}})
        cache = module.ActivityIndexCache(self.path)
        original = module.read_activity_entries
        def slow(path):
            time.sleep(.05)
            return original(path)
        with patch.object(module, 'read_activity_entries', side_effect=slow) as load:
            with concurrent.futures.ThreadPoolExecutor(max_workers=32) as pool:
                results = list(pool.map(lambda _: cache.get(), range(64)))
            self.assertEqual(load.call_count, 1)
            self.assertTrue(all(value is results[0] for value in results))

    def test_replacement_and_failure_keep_last_complete_generation(self):
        self.write({'entries': {'a': {'status': 'ok'}}})
        cache = module.ActivityIndexCache(self.path, refresh_seconds=0)
        first = cache.get()
        self.path.write_text('{"entries":{"a":', encoding='utf-8')
        self.assertIs(cache.get(), first)
        self.write({'entries': {'b': {'status': 'failed'}}})
        self.assertEqual(cache.get(), {'b': {'status': 'failed'}})
        self.assertNotIn('a', cache.get())

    def test_malformed_documents_are_rejected(self):
        for value in ['{"entries":{"a":{}}', '{"entries":{},}', '{"entries":{}} trailing',
                      '{"entries":{"a":1e}}', '{"entries":{"a":{},}}']:
            self.path.write_text(value, encoding='utf-8')
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.read_activity_entries(self.path, chunk_size=2)

    def test_missing_file_and_empty_archive(self):
        self.assertEqual(module.ActivityIndexCache(self.path).get(), {})
        for value in [{}, {'entries': {}}, {'entries': None}]:
            self.write(value)
            self.assertEqual(module.read_activity_entries(self.path), {})


if __name__ == '__main__':
    unittest.main()

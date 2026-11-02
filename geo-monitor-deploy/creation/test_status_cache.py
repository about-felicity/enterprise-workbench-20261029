import concurrent.futures
import threading
import unittest
from unittest.mock import patch

from .status_cache import StatusCache


class StatusCacheTests(unittest.TestCase):
    def test_concurrent_pollers_share_one_snapshot(self):
        cache = StatusCache()
        entered, release = threading.Event(), threading.Event()
        calls = []
        def build():
            calls.append(1)
            entered.set()
            self.assertTrue(release.wait(2))
            return {'at': 123, 'studio': {'daily_tasks': []}}
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
            first = pool.submit(cache.get, build)
            self.assertTrue(entered.wait(2))
            others = [pool.submit(cache.get, build) for _ in range(11)]
            release.set()
            results = [first.result()] + [f.result() for f in others]
        self.assertEqual(len(calls), 1)
        self.assertTrue(all(result is results[0] for result in results))

    def test_expiration_refreshes_external_worker_changes(self):
        cache = StatusCache()
        with patch('creation.status_cache.time.monotonic', return_value=10):
            self.assertEqual(cache.get(lambda: 'old'), 'old')
        with patch('creation.status_cache.time.monotonic', return_value=13):
            self.assertEqual(cache.get(lambda: 'new'), 'new')

    def test_action_invalidates_snapshot_and_inflight_result(self):
        cache = StatusCache()
        def build():
            cache.invalidate()
            return 'before action'
        cache.get(build)
        self.assertEqual(cache.get(lambda: 'after action'), 'after action')
        cache.invalidate()
        self.assertEqual(cache.get(lambda: 'after next action'), 'after next action')

    def test_errors_do_not_poison_or_deadlock_cache(self):
        cache = StatusCache()
        with self.assertRaises(ValueError):
            cache.get(lambda: (_ for _ in ()).throw(ValueError('unavailable')))
        self.assertEqual(cache.get(lambda: 'recovered'), 'recovered')

    def test_waiters_have_bounded_wait(self):
        cache = StatusCache(wait_timeout=0.01)
        cache.running = True
        with self.assertRaises(TimeoutError):
            cache.get(lambda: self.fail('must not start another scan'))

    def test_session_data_is_added_outside_shared_snapshot(self):
        cache = StatusCache()
        value = cache.get(lambda: {'at': 123})
        a = {**value, 'csrf': 'session-a'}
        b = {**cache.get(lambda: self.fail()), 'csrf': 'session-b'}
        self.assertNotEqual(a['csrf'], b['csrf'])
        self.assertNotIn('csrf', value)


if __name__ == '__main__':
    unittest.main()

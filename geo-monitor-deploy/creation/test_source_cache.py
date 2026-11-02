import hashlib
import tempfile
import unittest
from pathlib import Path
from geo_source_cards.runtime import atomic_json
from .source_cache import SourceCache, failure_kind


class SourceCacheTests(unittest.TestCase):
    def test_reuses_previous_round_without_extending_age(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); url = 'https://example.com/a'
            key = hashlib.sha256(url.encode()).hexdigest() + '.json'
            old = root / 'private_source_analysis-supplement-2/article_cache' / key
            atomic_json(old, dict(status='fetched', requested_url=url, fetched_at=100, text='body'))
            calls = []
            fetch = lambda u: calls.append(u) or dict(status='fetched', text='new')
            cache = SourceCache(root, fetch, clock=lambda: 200)
            self.assertEqual(cache(url)['text'], 'body')
            self.assertEqual(calls, [])
            # Downstream analysis stamps a new fetched_at; actual read age wins.
            result = {**cache(url), 'fetched_at': 86500}
            atomic_json(old, result)
            cache.clock = lambda: 86501
            self.assertEqual(cache(url)['text'], 'new')
            self.assertEqual(calls, [url])

    def test_dns_failure_retries_after_short_cooldown(self):
        with tempfile.TemporaryDirectory() as directory:
            calls = []; now = [100]
            def fetch(url):
                calls.append(url)
                return dict(status='failed', attempts=[dict(error='Temporary failure in name resolution')]) if len(calls)==1 else dict(status='fetched', text='recovered')
            cache = SourceCache(directory, fetch, clock=lambda: now[0])
            self.assertEqual(cache('https://example.com/a')['failure_kind'], 'dns')
            now[0] = 159
            self.assertEqual(cache('https://example.com/a')['status'], 'failed')
            self.assertEqual(len(calls), 1)
            now[0] = 160
            self.assertEqual(cache('https://example.com/a')['text'], 'recovered')

    def test_corrupt_and_wrong_url_cache_do_not_supply_content(self):
        with tempfile.TemporaryDirectory() as directory:
            url = 'https://example.com/a'; root = Path(directory)
            p = root/'source_read_cache'/(hashlib.sha256(url.encode()).hexdigest()+'.json')
            p.parent.mkdir();p.write_text('{')
            calls = []
            cache = SourceCache(root, lambda u: calls.append(u) or dict(status='fetched', text=u), clock=lambda:100)
            self.assertEqual(cache(url)['text'], url)
            atomic_json(p, dict(status='fetched', requested_url='https://example.com/b', fetched_at=100))
            self.assertEqual(cache(url)['text'], url)
            self.assertEqual(len(calls), 2)

    def test_failure_reasons(self):
        self.assertEqual(failure_kind(dict(attempts=[dict(error='HTTP 404')])), 'not_found')
        self.assertEqual(failure_kind(dict(error='Verification/access-denied page is not an article')), 'verification')


if __name__ == '__main__':
    unittest.main()

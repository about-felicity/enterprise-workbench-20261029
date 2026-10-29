import unittest

from collectors.wenxin.controller import WenxinWebCollector
from collectors.wenxin.wenxin_loop import security_backoff_seconds, should_retry_baidu_sources
from monitor_core.scheduling import build_question_schedule


class CollectorSmokeTests(unittest.TestCase):
    def test_baidu_search_url(self):
        self.assertIn("wd=", WenxinWebCollector.search_url("推荐一款护手霜"))

    def test_interleaved_schedule(self):
        self.assertEqual(
            build_question_schedule(["A", "B"], 2, "interleaved"),
            ["A", "B", "A", "B"],
        )

    def test_baidu_capture_retry_limit(self):
        self.assertTrue(should_retry_baidu_sources(False, 4, 5))
        self.assertFalse(should_retry_baidu_sources(False, 5, 5))
        self.assertGreaterEqual(security_backoff_seconds(2, 15), 180)


if __name__ == "__main__":
    unittest.main()

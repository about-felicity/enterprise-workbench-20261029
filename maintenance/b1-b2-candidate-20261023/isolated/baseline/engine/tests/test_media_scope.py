import unittest
from unittest.mock import Mock

from geo_source_cards.article_fetch import MediaScopedFetcher


class MediaScopeTests(unittest.TestCase):
    def test_registered_subdomains_are_fetched(self):
        fetch = Mock(return_value={"status": "fetched"})
        reader = MediaScopedFetcher(fetch, {"163.com": "网易"})
        self.assertEqual(reader("https://www.163.com/a")["status"], "fetched")
        fetch.assert_called_once()

    def test_unknown_sources_are_preserved_without_fetching(self):
        fetch = Mock()
        reader = MediaScopedFetcher(fetch, {"163.com": "网易"})
        url = "https://163.com.example.org/a"
        result = reader(url)
        self.assertEqual(result["status"], "unregistered_media")
        self.assertEqual(result["requested_url"], url)
        fetch.assert_not_called()

    def test_baidu_redirect_is_resolved_not_silently_dropped(self):
        fetch = Mock(return_value={"status": "fetched"})
        reader = MediaScopedFetcher(fetch, {})
        reader("https://www.baidu.com/link?url=abc")
        fetch.assert_called_once()

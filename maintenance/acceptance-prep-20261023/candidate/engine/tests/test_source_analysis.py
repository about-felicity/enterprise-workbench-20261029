import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from geo_source_cards import source_analysis as analysis


class SourceAnalysisTests(unittest.TestCase):
    def response(self, body, kind="text/html", status=200):
        response = Mock()
        response.status_code = status
        response.headers = {"Content-Type": kind}
        response.iter_content.return_value = [body.encode("utf8")]
        if status >= 400:
            response.raise_for_status.side_effect = requests.HTTPError(str(status))
        return response

    def fetch(self, response, **kwargs):
        session = Mock()
        session.get.return_value = response
        with patch.object(analysis, "validate_public_url"):
            return analysis.fetch_article(
                "https://example.com/article", session=session, **kwargs
            )

    def test_article_preserves_headline_and_discards_navigation_scripts(self):
        parser = analysis.ArticleParser()
        parser.feed(
            "<html><title>测试标题</title><nav>导航污染</nav><main><article><header><h1>文章标题</h1></header><p>"
            + "正文提到品牌甲。" * 30
            + "</p><script>脚本污染</script></article></main><footer>页脚污染</footer></html>"
        )
        result = parser.result()
        self.assertEqual(result["title"], "测试标题")
        self.assertIn("文章标题", result["text"])
        for term in ("导航污染", "脚本污染", "页脚污染"):
            self.assertNotIn(term, result["text"])

    def test_html_download_and_extract(self):
        response = self.response(
            "<article><p>" + "真实文章正文。" * 30 + "</p></article>"
        )
        result = self.fetch(response)
        self.assertEqual(result["status"], "fetched")
        self.assertEqual(len(result["sha256"]), 64)
        response.close.assert_called_once()

    def test_plain_text_download(self):
        result = self.fetch(
            self.response("正文数据。" * 30, "text/plain; charset=utf-8")
        )
        self.assertEqual(result["extraction_method"], "plain_text")

    def test_pdf_is_explicitly_unsupported(self):
        result = self.fetch(self.response("PDF", "application/pdf"))
        self.assertEqual(result["status"], "unsupported")
        self.assertEqual(result["text"], "")

    def test_http_failure_is_not_success(self):
        result = self.fetch(self.response("denied", status=403))
        self.assertEqual(result["status"], "failed")
        self.assertIn("403", result["error"])

    def test_size_limit_is_enforced(self):
        result = self.fetch(self.response("A" * 200), max_bytes=100)
        self.assertEqual(result["status"], "failed")
        self.assertIn("size limit", result["error"])

    def test_verification_html_is_not_article(self):
        result = self.fetch(
            self.response("<title>安全验证</title><p>" + "验证提示。" * 40 + "</p>")
        )
        self.assertEqual(result["status"], "failed")
        self.assertIn("verification", result["error"])

    def test_private_redirect_is_rejected_before_request(self):
        response = self.response("", status=302)
        response.headers["Location"] = "http://127.0.0.1/admin"
        session = Mock()
        session.get.return_value = response
        with patch.object(
            analysis,
            "validate_public_url",
            side_effect=[None, ValueError("non-public")],
        ):
            result = analysis.fetch_article("https://example.com", session=session)
        self.assertEqual(result["status"], "failed")
        session.get.assert_called_once()

    def test_public_url_rejects_local_and_credentials(self):
        with self.assertRaises(ValueError):
            analysis.validate_public_url("file:///etc/passwd")
        with self.assertRaises(ValueError):
            analysis.validate_public_url("https://name:password@example.com")
        with patch.object(
            analysis.socket,
            "getaddrinfo",
            return_value=[(2, 1, 6, "", ("127.0.0.1", 80))],
        ):
            with self.assertRaisesRegex(ValueError, "non-public"):
                analysis.validate_public_url("http://localhost")

    def test_deduplicated_download_and_persistent_cache(self):
        records = [
            {"body": "品牌甲 品牌甲", "sources": [{"url": "https://example.com/a"}]}
        ] * 2
        fetcher = Mock(
            return_value={
                "status": "fetched",
                "text": "品牌甲 优质正文",
                "final_url": "https://example.com/a",
            }
        )
        with tempfile.TemporaryDirectory() as temp:
            first = list(
                analysis.analyze_records(
                    records, brands=["品牌甲"], cache_dir=Path(temp), fetcher=fetcher
                )
            )
            second = list(
                analysis.analyze_records(
                    records, brands=["品牌甲"], cache_dir=Path(temp), fetcher=fetcher
                )
            )
        fetcher.assert_called_once()
        self.assertEqual(first, second)
        self.assertEqual(first[0]["answer_analysis"]["brand_mentions"]["品牌甲"], 2)
        self.assertEqual(
            first[0]["sources"][0]["content_analysis"]["brand_mentions"]["品牌甲"], 1
        )

    def test_failed_article_has_no_fabricated_content_metrics(self):
        with tempfile.TemporaryDirectory() as temp:
            rows = list(
                analysis.analyze_records(
                    [{"body": None, "sources": [{"url": "https://example.com"}]}],
                    cache_dir=Path(temp),
                    fetcher=lambda url: {
                        "status": "failed",
                        "text": "",
                        "error": "blocked",
                    },
                )
            )
        self.assertIsNone(rows[0]["sources"][0]["content_analysis"])
        self.assertFalse(rows[0]["answer_analysis"]["semantic_recommendation_inferred"])

    def test_no_fetch_makes_no_network_request(self):
        fetcher = Mock()
        with tempfile.TemporaryDirectory() as temp:
            rows = list(
                analysis.analyze_records(
                    [{"sources": [{"url": "https://example.com"}]}],
                    fetch=False,
                    cache_dir=Path(temp),
                    fetcher=fetcher,
                )
            )
        fetcher.assert_not_called()
        self.assertEqual(rows[0]["sources"][0]["article"]["status"], "not_fetched")

    def test_jsonl_and_array_inputs(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "input.json"
            for text in ('[{"body":"正文"}]', '{"body":"正文"}\n'):
                path.write_text(text, encoding="utf8")
                self.assertEqual(analysis.load_records(path), [{"body": "正文"}])
            path.write_text("[1]", encoding="utf8")
            with self.assertRaises(ValueError):
                analysis.load_records(path)

    def test_keyword_matches_are_literal_not_regex_or_recommendations(self):
        result = analysis.text_metrics(
            "A+B a+b 不推荐品牌甲", keywords=["a+b"], brands=["品牌甲"]
        )
        self.assertEqual(result["keyword_mentions"], {"a+b": 2})
        self.assertEqual(result["brand_mentions"], {"品牌甲": 1})
        self.assertFalse(result["semantic_recommendation_inferred"])


if __name__ == "__main__":
    unittest.main()

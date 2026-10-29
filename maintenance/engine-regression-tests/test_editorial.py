import argparse
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from geo_source_cards.article_fetch import (
    ScraplingArticleFetcher,
    check_article_relevance,
    extract_article,
)
from geo_source_cards.cli import questions_from_args
from geo_source_cards.editorial_analysis import (
    analyze_daily,
    build_prompt,
    review_draft,
)
from geo_source_cards.editorial_pipeline import prepare
from geo_source_cards.writer_handoff import verify_delivery, word_matches_draft

ARTICLE = (
    "如何选择适合自己的清洁产品。先记录自己的使用需求与偏好，再核对包装上的说明。不要只凭排行榜决定购买。"
    * 8
)


def observation(
    url, text=ARTICLE, model="deepseek", question="头屑多用什么洗发水比较好"
):
    return {
        "model": model,
        "question": question,
        "body": "测试回答",
        "sources": [
            {
                "url": url,
                "title": "测试文章",
                "article": {"status": "fetched", "title": "测试文章", "text": text},
            }
        ],
    }


class EditorialTests(unittest.TestCase):
    def test_unit_price_direction_and_missing_pump_volume_are_rejected(self):
        product = {
            "name": "示例产品",
            "brand": "示例",
            "facts": [],
            "forbidden_claims": [],
        }
        wrong = review_draft(
            "# 示例\n\n## 价格\n把毫升数除以实际到手价。\n\n## 用量\n如果每次两泵，一瓶200ml大约能撑一个月。",
            [],
            product,
            require_product_mention=False,
        )
        self.assertTrue(any("公式颠倒" in message for message in wrong["failures"]))
        self.assertTrue(any("每泵毫升数" in message for message in wrong["failures"]))
        valid = review_draft(
            "# 示例\n\n## 价格\n每毫升价格为到手总价除以总毫升数。\n\n## 用量\n记录实际用量后再计算。",
            [],
            product,
            require_product_mention=False,
        )
        self.assertFalse(
            any(
                "公式颠倒" in message or "每泵毫升数" in message
                for message in valid["failures"]
            )
        )

    def test_wrong_writer_marker_is_rejected_without_resending(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "writing_job.json").write_text(
                json.dumps({"job_id": "expected", "prompt_sha256": "abc"}),
                encoding="utf8",
            )
            (root / "writer_done.json").write_text(
                json.dumps({"job_id": "wrong"}), encoding="utf8"
            )
            with self.assertRaises(ValueError):
                verify_delivery(root)

    def test_incomplete_word_is_not_accepted(self):
        from zipfile import ZipFile

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.docx"
            with ZipFile(path, "w") as archive:
                archive.writestr(
                    "word/document.xml",
                    '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:p><w:r><w:t>一小段</w:t></w:r></w:p></w:document>',
                )
            with self.assertRaises(ValueError):
                word_matches_draft(path, ARTICLE)

    def test_domain_only_citation_title_is_not_a_relevance_failure(self):
        article = {"status": "fetched", "title": "实际文章标题", "text": ARTICLE}
        result = check_article_relevance(article, "m.dayi.org.cn")
        self.assertEqual(result["status"], "fetched")
        self.assertIsNone(result["title_relevance"])

    def test_unrelated_redirect_is_quarantined(self):
        article = {
            "status": "fetched",
            "title": "文化传播公司",
            "text": "品牌图文与活动内容策划，视觉协作。" * 15,
        }
        result = check_article_relevance(article, "去屑洗发水推荐头皮清洁产品选购")
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["text"], "")
        self.assertTrue(result["rejected_text"])

    def test_question_is_not_rewritten(self):
        question = "我是油头还有头屑选什么头皮清洁产品合适  "
        self.assertEqual(
            questions_from_args(
                argparse.Namespace(question=question, questions_file=None)
            ),
            [question],
        )

    def test_extraction_excludes_navigation(self):
        markup = (
            "<html><title>测试正文</title><nav>导航菜单</nav><article><h2>选择标准</h2><p>"
            + ARTICLE
            + "</p></article></html>"
        )
        article = extract_article(markup, "https://example.com/a")
        self.assertNotIn("导航菜单", article["text"])
        self.assertEqual(article["headings"], ["选择标准"])
        self.assertEqual(article["title"], "测试正文")

    def test_verification_is_never_an_article(self):
        with self.assertRaises(ValueError):
            extract_article("<title>安全验证</title><p>" + ARTICLE + "</p>")

    def test_scrapling_fallback_records_evidence(self):
        response = SimpleNamespace(
            status=200,
            headers={"content-type": "text/html"},
            url="https://example.com/a",
            body=b"a",
            html_content="<article><p>" + ARTICLE + "</p></article>",
        )

        def fail(url):
            raise ValueError("fixture HTTP failed")

        reader = ScraplingArticleFetcher(
            validator=lambda u: None,
            engines={"http": fail, "dynamic": lambda u: response},
        )
        result = reader("https://example.com/a")
        self.assertEqual(result["backend"], "dynamic")
        self.assertEqual(result["attempts"][0]["status"], "failed")
        self.assertTrue(result["scrapling_library"].endswith("__init__.py"))

    def test_reprints_cluster_and_daily_changes(self):
        rows = [
            observation("https://example.com/a"),
            observation("https://other.example/a", ARTICLE, "wenxin_card"),
        ]
        report = analyze_daily(
            rows,
            "2026-10-07",
            {"source_urls": ["https://old.example/a"], "dominant_structure": []},
        )
        self.assertEqual(report["counts"]["content_clusters"], 1)
        self.assertEqual(
            report["source_rankings"][0]["platforms"], ["deepseek", "wenxin_card"]
        )
        self.assertEqual(
            report["daily_changes"]["removed_urls"], ["https://old.example/a"]
        )
        self.assertEqual(len(report["daily_changes"]["new_urls"]), 2)
        self.assertTrue(report["source_rankings"][0]["evidence_sentences"])

    def test_modified_questions_do_not_contaminate_analysis(self):
        row = observation("https://example.com/a")
        row["wire_question"] = row["question"] + "请附上信源"
        report = analyze_daily([row], "2026-10-07")
        self.assertEqual(report["counts"]["unique_sources"], 0)
        self.assertEqual(
            report["excluded_observations"][0]["reason"], "question_was_modified"
        )

    def test_prompt_and_copy_detection(self):
        product = {
            "name": "示例产品",
            "demo": True,
            "facts": [],
            "forbidden_claims": ["保证根治"],
        }
        report = analyze_daily([observation("https://example.com/a")], "2026-10-07")
        prompt = build_prompt(report, product, job_id="test")
        self.assertIn("只使用 product.facts", prompt)
        self.assertIn("示例稿", prompt)
        draft = "# 标题\n示例稿\n## 一\n示例产品\n" + ARTICLE + "\n## 二\n保证根治"
        review = review_draft(
            draft,
            [{"url": "https://example.com/a", "text": ARTICLE}],
            product,
            min_chars=1,
        )
        self.assertTrue(
            any(
                message.startswith("发现连续复制来源文本的片段：")
                for message in review["failures"]
            )
        )
        self.assertIn("出现禁用表述：保证根治", review["failures"])

    def test_failed_sources_block_writing_and_preserve_records(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            row = observation("https://example.com/a")
            (root / "input.json").write_text(json.dumps([row]), encoding="utf8")
            (root / "product.json").write_text(
                json.dumps({"name": "示例产品", "facts": [], "demo": True}),
                encoding="utf8",
            )
            result = prepare(
                root / "input.json",
                root / "product.json",
                root / "job",
                "2026-10-07",
                fetcher=lambda url: {
                    "status": "failed",
                    "text": "",
                    "error": "fixture failure",
                },
            )
            self.assertEqual(result["status"], "blocked_no_article_text")
            self.assertFalse((root / "job/writing_prompt.md").exists())
            self.assertTrue((root / "job/observations.json").exists())


if __name__ == "__main__":
    unittest.main()

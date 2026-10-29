import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from geo_source_cards import cli
from geo_source_cards.api_prompts import expand_references
from geo_source_cards.runtime import atomic_json
from wenxin_monitor.controller import WenxinWebCollector


class CaptureRecoveryTests(unittest.TestCase):
    def test_required_wenxin_runs_before_optional_baidu_on_shared_lane(self):
        from geo_source_cards import server_capture
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            called = []
            def capture(command, **kw):
                model = command[command.index('--model') + 1]
                called.append(model)
                Path(command[command.index('--output') + 1]).write_text('{}\n', encoding='utf8')
                return SimpleNamespace(returncode=0)
            with patch.object(server_capture.subprocess, 'run', side_effect=capture), patch.object(server_capture, 'fetch_articles', return_value={'status':'blocked_no_article_text'}):
                server_capture.run_batch(root, root / 'questions.txt', root / 'product.json', '2026-10-10', subset=['baidu_ai', 'wenxin_card'])
            self.assertEqual(called, ['wenxin_card', 'baidu_ai'])

    def test_query_width_normalization_preserves_exact_question(self):
        question = '小孩头上有头皮屑小白点，推荐什么洗发水好'
        displayed = question.replace('，', ',')
        self.assertEqual(WenxinWebCollector._query_key(question), WenxinWebCollector._query_key(displayed))
        self.assertNotEqual(WenxinWebCollector._query_key(question), WenxinWebCollector._query_key('大人头上有头皮屑小白点，推荐什么洗发水好'))
        self.assertTrue(WenxinWebCollector._wenxin_question_matches({'url':'https://chat.baidu.com/search?word=' + displayed}, question))

    def test_bounded_recovery_keeps_success_after_tab_rotation_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = cli.parse_args(
                [
                    "--model",
                    "wenxin_card",
                    "--question",
                    "问题",
                    "--batch",
                    "recover",
                    "--output",
                    str(root / "rows.jsonl"),
                    "--bounded-search-recovery",
                ]
            )
            args.min_search_interval = 0
            collector = Mock()
            collector.reset_after_round.side_effect = RuntimeError("tab closed")
            result = {
                "body": "完整回答",
                "sources": [{"url": "https://example.org/a"}],
                "source_count": 1,
                "source_capture_complete": True,
            }
            with (
                patch.dict(os.environ, {"GEO_COLLECTOR_RUNTIME": directory}),
                patch.object(cli, "create_collector", return_value=collector),
                patch.object(
                    cli,
                    "collect_one",
                    side_effect=[RuntimeError("百度安全验证"), result],
                ) as call,
                patch("geo_source_cards.search_recovery.SearchRecovery.wait"),
                patch("geo_source_cards.search_recovery.SearchRecovery.evidence"),
            ):
                self.assertEqual(cli.run(args), 0)
                self.assertEqual(cli.run(args), 0)
            self.assertEqual(call.call_count, 2)
            self.assertEqual(
                len((root / "rows.jsonl").read_text("utf8").splitlines()), 1
            )

    def test_price_example_is_calculated_and_bound_without_model_arithmetic(self):
        from geo_source_cards.price_math import MARKER, example

        text = example()
        self.assertIn("0.158元/毫升", text)
        self.assertIn("0.225元/毫升", text)
        self.assertIn("A的单位容量价格低于B", text)
        result = expand_references(
            "writer", Path("."), {"draft_markdown": MARKER, "claim_map": {"claims": []}}
        )
        self.assertEqual(result["draft_markdown"], text)
        self.assertNotIn(MARKER, result["draft_markdown"])

    def test_review_hash_is_bound_to_immutable_local_draft(self):
        from geo_source_cards.daily_editorial import file_hash

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "draft.md").write_text("当前稿件", encoding="utf8")
            atomic_json(root / "claim_spans.json", {"C1": "当前稿件"})
            result = expand_references("review", root, {"claims": [{"span_id": "C1"}]})
            self.assertEqual(result["draft_sha256"], file_hash(root / "draft.md"))
            self.assertEqual(result["claims"][0]["text"], "当前稿件")

    def test_wenxin_current_search_host_matches_only_current_question(self):
        page = {"url": "https://chat.baidu.com/search?word=问题"}
        self.assertTrue(WenxinWebCollector._wenxin_question_matches(page, "问题"))
        self.assertFalse(WenxinWebCollector._wenxin_question_matches(page, "旧问题"))

    def test_navigation_refresh_is_bounded_and_bound_to_requested_url(self):
        collector = WenxinWebCollector.__new__(WenxinWebCollector)
        collector.page = Mock()
        collector.page.is_stealth = False
        collector.page.call.side_effect = [
            TimeoutError("Page.goto: Timeout"),
            {"loaderId": "new"},
        ]
        collector.page.evaluate.return_value = "https://chat.baidu.com/search?word=test"
        self.assertEqual(
            collector._navigate_fresh(collector.page.evaluate.return_value),
            "loader:new",
        )
        self.assertEqual(collector.page.call.call_count, 2)
        self.assertEqual(collector.page.call.call_args.args[0], "Page.reload")

    def test_navigation_does_not_refresh_wrong_page(self):
        collector = WenxinWebCollector.__new__(WenxinWebCollector)
        collector.page = Mock()
        collector.page.is_stealth = False
        collector.page.call.side_effect = TimeoutError("Page.goto: Timeout")
        collector.page.evaluate.return_value = "https://chat.baidu.com/search?word=old"
        with self.assertRaises(TimeoutError):
            collector._navigate_fresh("https://chat.baidu.com/search?word=new")
        self.assertEqual(collector.page.call.call_count, 1)

    def test_optional_baidu_records_failure_without_fabricating_absence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            args = cli.parse_args(
                [
                    "--model",
                    "baidu_ai",
                    "--question",
                    "问题",
                    "--batch",
                    "optional",
                    "--output",
                    str(root / "rows.jsonl"),
                    "--optional-baidu",
                ]
            )
            args.min_search_interval = 0
            collector = Mock()
            collector.collect_search.side_effect = RuntimeError("card still folded")
            with (
                patch.dict(
                    os.environ,
                    {"GEO_COLLECTOR_RUNTIME": str(root / "runtime")},
                    clear=False,
                ),
                patch.object(cli, "create_collector", return_value=collector),
            ):
                self.assertEqual(cli.run(args), 0)
                self.assertEqual(cli.run(args), 0)
            row = json.loads((root / "rows.jsonl").read_text("utf8"))
            self.assertEqual(row["availability"], "supplement_unavailable")
            self.assertFalse(row["body_capture_complete"])
            collector.collect_search.assert_called_once()

    def test_compact_research_binds_evidence_locally_and_rejects_unknown_id(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            atomic_json(root / "research_input.json", {"observations": []})
            atomic_json(
                root / "evidence_spans.json",
                {
                    "E1_1": {
                        "url": "https://example.com/a",
                        "quote": "这是保留在本地用于逐字验证的完整原文",
                    }
                },
            )
            response = {
                "units": [
                    {
                        "id": "KU01",
                        "kind": "opinion",
                        "text": "比较结构",
                        "evidence": ["E1_1"],
                    }
                ],
                "angle": "新角度",
                "sections": [],
                "gate": {},
            }
            result = expand_references("research", root, response)
            unit = result["knowledge_units"][0]
            self.assertEqual(unit["verification"], "not_independently_verified")
            self.assertEqual(unit["evidence"][0]["url"], "https://example.com/a")
            self.assertTrue(unit["evidence"][0]["quote"])
            response["units"][0]["evidence"] = ["E1_999"]
            with self.assertRaisesRegex(ValueError, "Unknown evidence"):
                expand_references("research", root, response)

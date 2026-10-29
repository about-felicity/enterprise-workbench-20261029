from __future__ import annotations

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock, patch

from geo_source_cards import cli
from wenxin_monitor.controller import WenxinWebCollector


class FakeCollector:
    def __init__(self, mode: str = "baidu_search_ai") -> None:
        self.mode = mode
        self.closed = False

    def collect_search(self, question: str, timeout: int = 90) -> dict:
        return {
            "capture_mode": self.mode,
            "body": "真实回答正文" * 12,
            "sources": [
                {"url": "https://example.com/a", "title": "文章", "media": "媒体"},
                {"url": "https://example.com/a", "title": "文章重复"},
            ],
        }

    def collect_wenxin_search(self, question: str, timeout: int = 90) -> dict:
        return {
            "capture_mode": "baidu_wenxin_search",
            "body": "文心正文" * 15,
            "sources": [{"url": "https://example.com/b", "title": "文心文章"}],
        }

    def collect(self, question: str, timeout: int = 240) -> dict:
        return {"body": "DeepSeek 正文" * 15, "sources": []}

    def close(self) -> None:
        self.closed = True


class CollectorTests(unittest.TestCase):
    def test_baidu_complete_prose_without_public_references_is_a_body_only_observation(self):
        with patch.object(WenxinWebCollector,'__init__',return_value=None):
            collector=cli.create_collector('baidu_ai')
        snapshot={'ok':True,'cardPresent':True,'folded':False,'readyState':'complete',
                  'query':'推荐一款防晒霜','body':'完整卡片正文'*20,'citationCount':0,
                  'url':'https://www.baidu.com/s?wd=推荐一款防晒霜'}
        collector.page=Mock()
        collector.page.evaluate.return_value=snapshot
        collector.public_card_references=Mock(return_value={'declared_count':0,'sources':[],
                                                          'drawer_opened':False,'card_present':True})
        with patch.object(cli.time,'sleep'):
            result=collector.collect_wenxin_search('推荐一款防晒霜')
        self.assertEqual(result['body'],snapshot['body'])
        self.assertEqual(result['availability'],'body_only')
        self.assertTrue(result['body_capture_complete'])
        self.assertFalse(result['source_capture_complete'])
        self.assertEqual(result['sources'],[])

    def test_complete_reference_entries_can_share_a_url(self):
        fake = FakeCollector()
        fake.collect = lambda question, timeout: {
            "body": "正文" * 20,
            "sources": [{"url": "https://example.com/a"}],
            "expected_source_count": 2,
            "source_capture_complete": True,
            "source_entries": [
                {"index": 1, "url": "https://example.com/a"},
                {"index": 2, "url": "https://example.com/a"},
            ],
        }
        self.assertTrue(
            cli.collect_one(fake, "deepseek", "问题")["source_capture_complete"]
        )

    def test_baidu_card_rejects_wenxin_fallback(self):
        with patch.object(WenxinWebCollector, "__init__", return_value=None):
            collector = cli.create_collector("baidu_ai")
        collector.page = Mock()
        collector.page.evaluate.return_value = {"ok": False}
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.object(cli, "runtime_root", return_value=Path(directory)),
        ):
            with self.assertRaisesRegex(RuntimeError, "不能用文心卡片代替"):
                collector.collect_wenxin_search("问题")

    def test_card_absence_requires_correct_query_and_loaded_search_results(self):
        snapshot = {
            "url": "https://www.baidu.com/s?wd=问题",
            "query": "问题",
            "readyState": "complete",
            "cardPresent": False,
            "searchResultsCount": 5,
        }
        self.assertTrue(cli.confirmed_no_card(snapshot, "问题"))
        for change in (
            {"query": "旧问题"},
            {"cardPresent": True},
            {"searchResultsCount": 0},
            {"readyState": "loading"},
            {"url": "https://example.com/s?wd=问题"},
        ):
            self.assertFalse(cli.confirmed_no_card({**snapshot, **change}, "问题"))

    def test_unproven_card_absence_is_not_saved_as_empty_answer(self):
        fake = FakeCollector()
        fake.collect_search = lambda question, timeout: {
            "capture_mode": "baidu_search_ai",
            "availability": "no_card",
            "body": "",
            "sources": [],
            "absence_evidence": {},
        }
        with self.assertRaisesRegex(RuntimeError, "正文为空"):
            cli.collect_one(fake, "baidu_ai", "问题")

    def test_models_keep_distinct_capture_modes_and_deduplicate_links(self):
        fake = FakeCollector()
        baidu = cli.collect_one(fake, "baidu_ai", "问题")
        self.assertEqual(baidu["source_count"], 1)
        self.assertEqual(baidu["sources"][0]["media"], "媒体")
        self.assertEqual(
            cli.collect_one(fake, "wenxin_card", "问题")["capture_mode"],
            "baidu_wenxin_search",
        )
        self.assertIn("DeepSeek", cli.collect_one(fake, "deepseek", "问题")["body"])
        fake.mode = "baidu_wenxin_search"
        with self.assertRaisesRegex(RuntimeError, "模式不匹配"):
            cli.collect_one(fake, "baidu_ai", "问题")

    def test_deepseek_rate_limit_persists_across_calls(self):
        with tempfile.TemporaryDirectory() as temp:
            state = Path(temp) / "rate.json"
            now = [1000.0]
            sleeps: list[float] = []

            def sleep(seconds: float) -> None:
                sleeps.append(seconds)
                now[0] += seconds

            cli.wait_for_deepseek_slot(state, clock=lambda: now[0], sleep=sleep)
            now[0] += 30
            cli.wait_for_deepseek_slot(state, clock=lambda: now[0], sleep=sleep)
            self.assertEqual(sleeps, [270.0])
            self.assertEqual(json.loads(state.read_text())["last_prompt_epoch"], 1300.0)
            with self.assertRaises(ValueError):
                cli.wait_for_deepseek_slot(state, 299)

    def test_cli_writes_separate_rounds_without_live_browser(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "results.jsonl"
            fake = FakeCollector()
            args = Namespace(
                model="baidu_ai",
                question="测试问题",
                questions_file=None,
                rounds=2,
                ready=False,
                show_browser=False,
                output=output,
                min_deepseek_interval=300,
                min_search_interval=0,
                runtime_dir=Path(temp) / "runtime",
            )
            with (
                patch.dict("os.environ"),
                patch.object(cli, "create_collector", return_value=fake),
            ):
                self.assertEqual(cli.run(args), 0)
            rows = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([row["round"] for row in rows], [1, 2])
            self.assertEqual(rows[1]["duplicate_of"], "baidu_ai:测试问题:1")
            self.assertTrue(fake.closed)


if __name__ == "__main__":
    unittest.main()

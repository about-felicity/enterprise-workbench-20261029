import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from geo_source_cards.api_budget import Budget, BudgetExceeded, usage_cost
from geo_source_cards.deepseek_api import APIError, DeepSeekClient
from geo_source_cards.pipeline_control import (
    BEIJING,
    pause,
    resume,
    save_settings,
    state,
)
from geo_source_cards.prompt_compaction import compact_input
from geo_source_cards.runtime import atomic_json
from geo_source_cards.scheduler import due


class ControlsTests(unittest.TestCase):
    def test_per_article_research_is_not_charged_against_other_articles(self):
        save_settings(self.root, {'article_budget_cny':0.02})
        for number in (1,2):
            ident=self.budget.reserve(self.payload,self.root/f'research-{number}',
                                      {**self.meta,'number':number,'cost_scope':'article'},'research')
            self.budget.settle(ident,{'prompt_tokens':1000,'completion_tokens':1500})
        self.budget.reserve(self.payload,self.root/'writer-3',{**self.meta,'number':3},'writer')
        # Retries of the same article still consume its own original research.
        with self.assertRaisesRegex(BudgetExceeded,'单篇'):
            self.budget.reserve(self.payload,self.root/'writer-1',self.meta,'writer')
        rows=self.budget.summary()['calls']
        self.assertEqual({r['article'] for r in rows if r['stage']=='research'},{'1','2'})

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.budget = Budget(self.root, test=True)
        self.addCleanup(self.budget.close)
        self.payload = {
            "messages": [{"role": "user", "content": "测试"}],
            "max_tokens": 2000,
        }
        self.meta = {"date": "2026-10-08", "category": "选购", "number": 1}

    def test_unknown_delivery_keeps_full_reservation_and_survives_restart(self):
        ident = self.budget.reserve(
            self.payload, self.root / "one", self.meta, "writer"
        )
        self.budget.settle(ident, None)
        another = Budget(self.root, test=True)
        self.addCleanup(another.close)
        self.assertGreater(another.summary()["reserved_cny"], 0)
        with self.assertRaises(BudgetExceeded):
            another.reserve(self.payload, self.root / "one", self.meta, "writer")

    def test_article_cap_counts_failed_attempts_and_shared_analysis(self):
        save_settings(self.root, {"article_budget_cny": 0.02})
        tax = self.budget.reserve(
            self.payload, self.root / "tax", {"date": self.meta["date"]}, "taxonomy"
        )
        self.budget.settle(tax, {"prompt_tokens": 1000, "completion_tokens": 1500})
        # .014 shared + >.016 reserved exceeds .03; no request row is created.
        with self.assertRaisesRegex(BudgetExceeded, "单篇"):
            self.budget.reserve(self.payload, self.root / "writer", self.meta, "writer")
        self.assertEqual(len(self.budget.summary()["calls"]), 1)

    def test_test_cap_is_lifetime_not_reset_by_date(self):
        save_settings(self.root, {"test_budget_cny": 0.02})
        self.budget.reserve(self.payload, self.root / "one", self.meta, "writer")
        with self.assertRaisesRegex(BudgetExceeded, "开发测试"):
            self.budget.reserve(
                self.payload,
                self.root / "two",
                {**self.meta, "date": "2026-10-09"},
                "writer",
            )

    def test_daily_cap_is_shared_across_categories(self):
        save_settings(self.root, {"daily_budget_cny": 0.02})
        self.budget.reserve(self.payload, self.root / "one", self.meta, "writer")
        with self.assertRaisesRegex(BudgetExceeded, "每日"):
            self.budget.reserve(
                self.payload,
                self.root / "two",
                {**self.meta, "category": "其他"},
                "writer",
            )

    def test_usage_uses_cache_hits_and_keeps_unknown_usage_unsettled(self):
        self.assertAlmostEqual(
            usage_cost(
                {
                    "prompt_tokens": 1000,
                    "prompt_cache_hit_tokens": 500,
                    "completion_tokens": 100,
                }
            ),
            0.00182,
        )
        self.assertIsNone(usage_cost({}))
        self.assertIsNone(usage_cost({"prompt_tokens": -1, "completion_tokens": 10}))

    def test_offpeak_pricing_never_discounts_a_peak_crossing(self):
        from geo_source_cards.api_budget import settled_price_factor

        at = lambda hour, minute=0: datetime(
            2026, 10, 9, hour, minute, tzinfo=BEIJING
        ).timestamp()
        self.assertEqual(settled_price_factor(at(8), at(8, 30)), 0.5)
        self.assertEqual(settled_price_factor(at(8, 59), at(9)), 1)
        self.assertEqual(settled_price_factor(at(12), at(13)), 0.5)
        self.assertEqual(settled_price_factor(at(13, 59), at(14)), 1)
        self.assertEqual(settled_price_factor(at(18), at(19)), 0.5)
        self.assertEqual(settled_price_factor(at(18), at(17)), 1)

    def test_resume_requires_fresh_check_after_latest_pause_and_settings(self):
        pause(self.root, "login_required", "请登录")
        with self.assertRaises(ValueError):
            resume(self.root)
        import time

        atomic_json(
            self.root / "environment_check.json",
            {
                "ok": True,
                "checked_epoch": time.time(),
                "control_revision": state(self.root)["revision"],
            },
        )
        save_settings(self.root, {"max_per_category": 10})
        with self.assertRaises(ValueError):
            resume(self.root)
        atomic_json(
            self.root / "environment_check.json",
            {
                "ok": True,
                "checked_epoch": time.time(),
                "control_revision": state(self.root)["revision"],
            },
        )
        self.assertFalse(resume(self.root)["paused"])
        with self.assertRaises(ValueError):
            resume(self.root)  # same check cannot authorize another resume

    def test_restored_login_does_not_unpause_or_start_scheduler(self):
        pause(self.root, "login_required", "请登录")
        atomic_json(
            self.root / "collectors/deepseek/deepseek_session.json", {"status": "ready"}
        )
        self.assertIsNone(due(self.root, datetime(2026, 10, 8, 6, tzinfo=BEIJING)))
        self.assertTrue(state(self.root)["paused"])

    def test_schedule_time_and_same_day_deduplication(self):
        self.assertIsNone(due(self.root, datetime(2026, 10, 8, 4, 59, tzinfo=BEIJING)))
        self.assertEqual(
            due(self.root, datetime(2026, 10, 8, 5, tzinfo=BEIJING)), "2026-10-08"
        )
        atomic_json(
            self.root / "scheduler.json", {"date": "2026-10-08", "status": "completed"}
        )
        self.assertIsNone(due(self.root, datetime(2026, 10, 8, 10, tzinfo=BEIJING)))

    def test_resume_original_batch_across_midnight(self):
        atomic_json(
            self.root / "scheduler.json",
            {"date": "2026-10-08", "status": "paused", "attempt_epoch": 100},
        )
        atomic_json(
            self.root / "control.json",
            {"paused": False, "resume_requested": True, "resumed_epoch": 200},
        )
        self.assertEqual(
            due(self.root, datetime(2026, 10, 9, 6, tzinfo=BEIJING)), "2026-10-08"
        )

    def test_settings_reject_unsafe_time_and_unbounded_revisions(self):
        for changes in (
            {"start_time": "25:00"},
            {"max_per_category": 0},
            {"max_revisions": 2},
            {"daily_budget_cny": float("nan")},
            {"deepseek_interval": 299},
        ):
            with self.assertRaises(ValueError):
                save_settings(self.root, changes)

    def test_compaction_keeps_all_urls_and_literal_evidence(self):
        text = "如果更喜欢清淡香气，可以先比较香型说明。" * 500
        data = {
            "articles": [{"url": "https://media.example/a", "article": {"text": text}}]
        }
        compacted = compact_input("taxonomy", data)
        self.assertEqual(compacted["articles"][0]["url"], data["articles"][0]["url"])
        extract = compacted["articles"][0]["article"]["text"]
        self.assertLess(len(extract), 1000)
        for part in extract.split("\n[…]\n"):
            self.assertIn(part, text)
        self.assertEqual(data["articles"][0]["article"]["text"], text)

    def test_evidence_ids_cannot_be_rebound_to_other_source(self):
        from geo_source_cards.api_prompts import evidence_spans, expand_references

        data = {
            "articles": [
                {
                    "url": "https://media.example/a",
                    "article": {
                        "text": "比较产品容量和包装形式有助于区分不同购买需求。"
                    },
                }
            ]
        }
        index = evidence_spans(data, "taxonomy")
        atomic_json(self.root / "evidence_spans.json", index)
        value = {
            "categories": [
                {"sources": [{"url": "https://media.example/b", "quote_id": "E1_1"}]}
            ]
        }
        with self.assertRaises(ValueError):
            expand_references("taxonomy", self.root, value)
        value["categories"][0]["sources"][0]["url"] = "https://media.example/a"
        result = expand_references("taxonomy", self.root, value)
        self.assertEqual(
            result["categories"][0]["sources"][0]["quote"], index["E1_1"]["quote"]
        )

    def test_review_ids_restore_exact_current_draft_text(self):
        from geo_source_cards.api_prompts import expand_references

        atomic_json(self.root / "claim_spans.json", {"C1": "产品资料标注规格为200ml。"})
        (self.root / "draft.md").write_text("产品资料标注规格为200ml。", encoding="utf8")
        result = expand_references("review", self.root, {"claims": [{"span_id": "C1"}]})
        self.assertEqual(result["claims"][0]["text"], "产品资料标注规格为200ml。")
        with self.assertRaises(ValueError):
            expand_references("review", self.root, {"claims": [{"span_id": "C99"}]})

    def make_client(self):
        key = self.root / "key"
        key.write_text("sk-" + "a" * 32, encoding="utf8")
        session = Mock()
        session.get.return_value.status_code = 200
        session.get.return_value.json.return_value = {
            "is_available": True,
            "balance_infos": [],
        }
        return DeepSeekClient(key, session=session, budget=self.budget), session

    def test_empty_balance_never_sends_completion(self):
        client, session = self.make_client()
        session.get.return_value.json.return_value["is_available"] = False
        with self.assertRaisesRegex(APIError, "balance_insufficient"):
            client.complete("test", self.root / "call", meta=self.meta)
        session.post.assert_not_called()
        self.assertTrue(state(self.root)["paused"])

    def test_budget_rejection_happens_before_post(self):
        client, session = self.make_client()
        save_settings(self.root, {"article_budget_cny": 0.001})
        with self.assertRaisesRegex(APIError, "budget_exceeded"):
            client.complete("test", self.root / "call", meta=self.meta)
        session.post.assert_not_called()

    def test_timeout_never_releases_budget_or_retries(self):
        client, session = self.make_client()
        session.post.side_effect = requests.Timeout()
        with self.assertRaises(APIError):
            client.complete("test", self.root / "call", meta=self.meta)
        with self.assertRaises(APIError):
            client.complete("test", self.root / "call", meta=self.meta)
        self.assertEqual(session.post.call_count, 1)
        self.assertGreater(self.budget.summary()["reserved_cny"], 0)
        self.assertEqual(
            session.post.call_args.kwargs["json"]["thinking"]["type"], "disabled"
        )

    def test_login_loss_before_send_is_pending_but_after_send_is_quarantined(self):
        from argparse import Namespace

        from geo_source_cards import cli
        from geo_source_cards.journal import Journal
        from geo_source_cards.session_watch import LoginRequiredError

        for sent in (False, True):
            folder = self.root / str(sent)
            args = Namespace(
                model="deepseek",
                question="原始问题",
                questions_file=None,
                rounds=1,
                ready=False,
                show_browser=False,
                output=folder / "result.jsonl",
                min_deepseek_interval=300,
                runtime_dir=folder,
                batch="single",
            )
            collector = Mock()
            collector.assert_session = Mock()
            collector.check_ready.return_value = {"ok": True}
            collector.submission_started = sent
            collector.collect.side_effect = LoginRequiredError("已掉登录")
            with (
                patch.dict("os.environ", {"GEO_PIPELINE_ROOT": str(folder)}),
                patch.object(cli, "create_collector", return_value=collector),
                self.assertRaises(LoginRequiredError),
            ):
                cli.run(args)
            journal = Journal(folder / "tasks.sqlite")
            try:
                record = journal.db.execute("select state from captures").fetchone()
                self.assertEqual(
                    record["state"], "needs_attention" if sent else "pending"
                )
                self.assertTrue(state(folder)["paused"])
            finally:
                journal.close()


if __name__ == "__main__":
    unittest.main()

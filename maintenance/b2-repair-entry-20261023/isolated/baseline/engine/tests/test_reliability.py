import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from test_collectors import FakeCollector

from geo_source_cards import cli
from geo_source_cards.journal import Journal
from geo_source_cards.runtime import process_lock
from monitor_core.cdp_chat import CDPPage
from web_collectors import browser
from web_collectors.collector import BrowserCollector, conversation_id
from web_collectors.config import site_config
from wenxin_monitor.controller import (
    BAIDU_AI_SNAPSHOT_JS,
    ScraplingStealthPage,
    WenxinWebCollector,
)


class ReliabilityTests(unittest.TestCase):
    def test_slow_navigation_waits_without_searching_twice(self):
        adapter = ScraplingStealthPage.__new__(ScraplingStealthPage)
        adapter.page = Mock()
        adapter.page.goto.side_effect = TimeoutError("Page.goto: Timeout 15000ms exceeded")
        result = adapter.call("Page.navigate", {"url": "https://www.baidu.com/s?wd=test"})
        self.assertIn("frameId", result)
        adapter.page.goto.assert_called_once()
        adapter.page.wait_for_load_state.assert_called_once_with("domcontentloaded", timeout=45000)

    def test_navigation_failure_is_not_silently_retried(self):
        adapter = ScraplingStealthPage.__new__(ScraplingStealthPage)
        adapter.page = Mock()
        adapter.page.goto.side_effect = RuntimeError("navigation disconnected")
        with self.assertRaisesRegex(RuntimeError, "disconnected"):
            adapter.call("Page.navigate", {"url": "https://www.baidu.com/"})
        adapter.page.goto.assert_called_once()
        adapter.page.wait_for_load_state.assert_not_called()

    def test_slow_navigation_remains_failed_when_document_never_loads(self):
        adapter = ScraplingStealthPage.__new__(ScraplingStealthPage)
        adapter.page = Mock()
        adapter.page.goto.side_effect = TimeoutError("Page.goto: Timeout 15000ms exceeded")
        adapter.page.wait_for_load_state.side_effect = TimeoutError("document not loaded")
        with self.assertRaisesRegex(TimeoutError, "document not loaded"):
            adapter.call("Page.navigate", {"url": "https://www.baidu.com/"})
        adapter.page.goto.assert_called_once()

    def test_deepseek_empty_body_on_old_conversation_is_not_fresh(self):
        collector = BrowserCollector.__new__(BrowserCollector)
        collector.page = Mock()
        collector.page.evaluate.return_value = None
        collector._snapshot = Mock(
            return_value={
                "url": "https://chat.deepseek.com/a/chat/s/old-chat",
                "readyState": "complete",
                "body": "",
                "busy": False,
            }
        )
        with (
            patch("web_collectors.collector.time.monotonic", side_effect=[0, 0, 11]),
            patch("web_collectors.collector.time.sleep"),
        ):
            with self.assertRaisesRegex(RuntimeError, "question was not sent"):
                collector._start_fresh_chat()
        collector.page.click.assert_not_called()

    def test_deepseek_fresh_home_and_identity_are_verified(self):
        collector = BrowserCollector.__new__(BrowserCollector)
        collector.page = Mock()
        collector.page.evaluate.return_value = None
        collector._snapshot = Mock(
            return_value={
                "url": "https://chat.deepseek.com/",
                "readyState": "complete",
                "body": "",
                "busy": False,
            }
        )
        self.assertEqual(
            collector._start_fresh_chat()["empty_chat_url"],
            "https://chat.deepseek.com/",
        )
        self.assertEqual(
            conversation_id("https://chat.deepseek.com/a/chat/s/abc-123"), "abc-123"
        )
        self.assertEqual(conversation_id("https://example.com/a/chat/s/abc-123"), "")

    def test_repeated_baidu_search_requires_new_document_even_same_question(self):
        page = Mock()
        page.is_stealth = True
        page.call.return_value = {"frameId": "same-tab"}
        page.evaluate.side_effect = ["100", "200", "200", "200"]
        collector = WenxinWebCollector(page=page)
        self.addCleanup(collector.close)
        self.assertEqual(
            collector._navigate_fresh("https://www.baidu.com/s?wd=问题"),
            "frame:same-tab:time:200",
        )
        with self.assertRaisesRegex(RuntimeError, "拒绝复用"):
            collector._navigate_fresh("https://www.baidu.com/s?wd=问题")
        self.assertEqual(page.call.call_count, 2)

    def test_wenxin_redirect_requires_exact_current_question(self):
        result = {
            "url": "https://wenxin.baidu.com/search/123?enter_type=unknown",
            "pageText": "返回\n原始问题\n回答正文",
        }
        self.assertTrue(WenxinWebCollector._wenxin_question_matches(result, "原始问题"))
        self.assertFalse(WenxinWebCollector._wenxin_question_matches(result, "另一题"))
        self.assertFalse(
            WenxinWebCollector._wenxin_question_matches(
                {**result, "pageText": "回答中提到了原始问题"}, "原始问题"
            )
        )
        self.assertFalse(
            WenxinWebCollector._wenxin_question_matches(
                {**result, "url": "https://example.com/search/123"}, "原始问题"
            )
        )

    def test_read_failure_recovery_excludes_deepseek_and_is_once_only(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            contextlib.closing(Journal(Path(directory) / "tasks.sqlite")) as journal,
        ):
            for model in ("baidu_ai", "deepseek"):
                task = journal.plan(
                    model, model, ["问题"], 1, Path(directory) / (model + ".jsonl")
                )[0]
                journal.start(task["task_id"])
                journal.fail(
                    task["task_id"],
                    RuntimeError("Page.evaluate: Execution context was destroyed"),
                )
                recovered = journal.recover_read_failures(model)
                self.assertEqual(recovered, 1 if model == "baidu_ai" else 0)
                if recovered:
                    journal.start(task["task_id"])
                    journal.fail(
                        task["task_id"],
                        RuntimeError("Page.evaluate: Execution context was destroyed"),
                    )
                    self.assertEqual(journal.recover_read_failures(model), 0)
            self.assertEqual(
                journal.db.execute("select count(*) from read_recoveries").fetchone()[
                    0
                ],
                1,
            )

    def test_known_readonly_snapshot_recovers_from_navigation(self):
        page = ScraplingStealthPage.__new__(ScraplingStealthPage)
        page.timeout_ms = 60000
        page.page = Mock()
        page.page.evaluate.side_effect = [
            RuntimeError(
                "Execution context was destroyed, most likely because of a navigation."
            ),
            {"ok": True},
        ]
        with patch("wenxin_monitor.controller.time.sleep"):
            self.assertEqual(page.evaluate(BAIDU_AI_SNAPSHOT_JS), {"ok": True})
        self.assertEqual(page.page.evaluate.call_count, 2)

    def test_arbitrary_evaluation_is_never_replayed_on_navigation(self):
        page = ScraplingStealthPage.__new__(ScraplingStealthPage)
        page.timeout_ms = 60000
        page.page = Mock()
        page.page.evaluate.side_effect = RuntimeError("Execution context was destroyed")
        with self.assertRaises(RuntimeError):
            page.evaluate("document.querySelector('button').click()")
        page.page.evaluate.assert_called_once()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        env = patch.dict(
            os.environ, {"GEO_COLLECTOR_RUNTIME": str(self.root / "runtime")}
        )
        env.start()
        self.addCleanup(env.stop)
        self.args = cli.parse_args(
            [
                "--model",
                "baidu_ai",
                "--question",
                "问题",
                "--batch",
                "regression",
                "--output",
                str(self.root / "answer.jsonl"),
            ]
        )
        self.args.min_search_interval = 0

    def test_baidu_and_wenxin_share_persistent_search_interval(self):
        path = self.root / "last_search.json"
        now = [1000]
        cli.wait_for_search_slot(path, clock=lambda: now[0])
        now[0] += 10
        pauses = []
        def sleep(seconds):
            pauses.append(seconds)
            now[0] += seconds
        cli.wait_for_search_slot(path, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(pauses, [50])
        self.assertEqual(json.loads(path.read_text())["last_search_epoch"], 1060)

    def run_quietly(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return cli.run(self.args)

    def test_completed_batch_resume_does_not_create_browser(self):
        with patch.object(cli, "create_collector", return_value=FakeCollector()):
            self.run_quietly()
        before = self.args.output.read_text(encoding="utf8")
        with patch.object(cli, "create_collector") as create:
            self.assertEqual(self.run_quietly(), 0)
            create.assert_not_called()
        self.assertEqual(self.args.output.read_text(encoding="utf8"), before)

    def test_interrupted_submission_requires_attention_without_resending(self):
        journal = Journal(self.root / "runtime/tasks.sqlite")
        task = journal.plan("regression", "baidu_ai", ["问题"], 1, self.args.output)[0]
        journal.start(task["task_id"])
        journal.close()
        with patch.object(cli, "create_collector") as create:
            with self.assertRaisesRegex(RuntimeError, "uncertain"):
                self.run_quietly()
            create.assert_not_called()
        journal = Journal(self.root / "runtime/tasks.sqlite")
        self.addCleanup(journal.close)
        self.assertEqual(
            journal.db.execute("select state from captures").fetchone()[0],
            "needs_attention",
        )

    def test_export_failure_after_commit_is_recovered_without_resending(self):
        original = Journal.export
        calls = []

        def export(journal, output):
            calls.append(output)
            if len(calls) == 2:
                raise OSError("simulated disk error")
            return original(journal, output)

        with (
            patch.object(cli, "create_collector", return_value=FakeCollector()),
            patch.object(Journal, "export", export),
        ):
            with self.assertRaises(OSError):
                self.run_quietly()
        with patch.object(cli, "create_collector") as create:
            self.run_quietly()
            create.assert_not_called()
        self.assertEqual(
            len(self.args.output.read_text(encoding="utf8").splitlines()), 1
        )

    def test_changed_batch_parameters_are_rejected(self):
        with patch.object(cli, "create_collector", return_value=FakeCollector()):
            self.run_quietly()
        self.args.question = "不同的问题"
        with self.assertRaisesRegex(ValueError, "parameters"):
            self.run_quietly()

    def test_unmanaged_output_is_preserved(self):
        self.args.output.write_text("original evidence", encoding="utf8")
        with self.assertRaisesRegex(RuntimeError, "preserve"):
            self.run_quietly()
        self.assertEqual(self.args.output.read_text(), "original evidence")

    def test_partial_or_unknown_sources_can_be_required_to_fail(self):
        self.args.require_complete_sources = True
        with patch.object(cli, "create_collector", return_value=FakeCollector()):
            with self.assertRaisesRegex(RuntimeError, "not proven"):
                self.run_quietly()
        self.assertEqual(self.args.output.read_text(), "")
        journal = Journal(self.root / "runtime/tasks.sqlite")
        self.addCleanup(journal.close)
        row = journal.db.execute("select result from captures").fetchone()
        self.assertIn("真实回答正文", json.loads(row[0])["body"])

    def test_duplicate_detection_survives_pending_batch_resume(self):
        self.args.rounds = 2
        journal = Journal(self.root / "runtime/tasks.sqlite")
        first = journal.plan("regression", "baidu_ai", ["问题"], 2, self.args.output)[0]
        journal.start(first["task_id"])
        record = cli.collect_one(FakeCollector(), "baidu_ai", "问题")
        journal.complete(first["task_id"], {**record, "round": 1})
        journal.close()
        with patch.object(cli, "create_collector", return_value=FakeCollector()):
            self.run_quietly()
        rows = [
            json.loads(line)
            for line in self.args.output.read_text(encoding="utf8").splitlines()
        ]
        self.assertEqual(rows[1]["duplicate_of"], "baidu_ai:问题:1")

    def test_readiness_false_returns_nonzero(self):
        self.args.ready = True
        self.args.model = "deepseek"
        fake = Mock()
        fake.check_ready.return_value = {"ok": False}
        with patch.object(cli, "create_collector", return_value=fake):
            self.assertEqual(self.run_quietly(), 2)
        fake.collect.assert_not_called()
        fake.close.assert_called_once()

    def test_corrupt_rate_state_does_not_bypass_interval(self):
        path = self.root / "rate.json"
        path.write_text("{broken")
        with self.assertRaisesRegex(RuntimeError, "refusing"):
            cli.wait_for_deepseek_slot(path)
        self.assertEqual(path.read_text(), "{broken")

    def test_input_timeout_is_never_replayed(self):
        page = CDPPage.__new__(CDPPage)
        for method in ("Input.dispatchKeyEvent", "Runtime.evaluate", "Page.navigate"):
            page._call_once = Mock(side_effect=TimeoutError("reply lost"))
            page.connect = Mock()
            with self.assertRaises(TimeoutError):
                page.call(method)
            page._call_once.assert_called_once()
            page.connect.assert_not_called()

    def test_read_only_timeout_reconnects_once(self):
        page = CDPPage.__new__(CDPPage)
        page._call_once = Mock(side_effect=[TimeoutError(), {"cookies": []}])
        page.connect = Mock()
        self.assertEqual(page.call("Network.getAllCookies"), {"cookies": []})
        self.assertEqual(page._call_once.call_count, 2)
        page.connect.assert_called_once()

    def test_persistent_login_survives_launch_failure(self):
        profile = self.root / "runtime/web_profiles/deepseek"
        profile.mkdir(parents=True)
        cookie = profile / "Cookies"
        cookie.write_bytes(b"login evidence")
        with (
            patch.object(browser, "port_open", return_value=False),
            patch.object(browser, "chrome_executable", return_value=Path("chrome")),
            patch.object(
                browser.subprocess, "Popen", side_effect=OSError("launch failed")
            ),
        ):
            with self.assertRaises(OSError):
                browser.launch_browser(site_config("deepseek"), headless=True)
        self.assertEqual(cookie.read_bytes(), b"login evidence")

    def test_persistent_login_survives_launch_timeout(self):
        profile = self.root / "runtime/web_profiles/deepseek"
        profile.mkdir(parents=True)
        cookie = profile / "Cookies"
        cookie.write_bytes(b"login evidence")
        with (
            patch.object(browser, "port_open", return_value=False),
            patch.object(browser, "chrome_executable", return_value=Path("chrome")),
            patch.object(browser.subprocess, "Popen") as process,
            patch.object(browser.time, "monotonic", side_effect=[0, 31]),
        ):
            with self.assertRaisesRegex(RuntimeError, "启动超时"):
                browser.launch_browser(site_config("deepseek"), headless=True)
            process.return_value.terminate.assert_called_once()
        self.assertEqual(cookie.read_bytes(), b"login evidence")

    def test_process_lock_excludes_another_process(self):
        path = self.root / "collector.lock"
        script = "from pathlib import Path; from geo_source_cards.runtime import process_lock; import sys\ntry:\n with process_lock(Path(sys.argv[1])): pass\nexcept RuntimeError: sys.exit(7)"
        with process_lock(path):
            result = subprocess.run(
                [sys.executable, "-c", script, str(path)],
                capture_output=True,
                timeout=15,
            )
        self.assertEqual(result.returncode, 7, result.stderr.decode())
        with process_lock(path):
            pass

    def test_zero_unverified_sources_are_unknown(self):
        collector = BrowserCollector.__new__(BrowserCollector)
        collector.site = site_config("deepseek")
        result = collector._capture_result(
            {"body": "完整回答正文，测试时没有信源。", "sources": []}, "问题"
        )
        self.assertIsNone(result["source_capture_complete"])
        self.assertEqual(result["source_capture_status"], "unknown")

    def test_known_source_total_detects_incomplete_and_complete(self):
        collector = BrowserCollector.__new__(BrowserCollector)
        collector.site = site_config("deepseek")
        snapshot = {
            "body": "完整回答正文用于测试信源数量。",
            "sources": [{"url": "https://example.com"}],
            "expected_source_count": 2,
        }
        self.assertIs(
            collector._capture_result(snapshot, "问题")["source_capture_complete"],
            False,
        )
        snapshot["expected_source_count"] = 1
        self.assertIs(
            collector._capture_result(snapshot, "问题")["source_capture_complete"], True
        )

    def test_normalization_does_not_count_invalid_or_duplicate_sources(self):
        fake = FakeCollector()
        fake.collect = Mock(
            return_value={
                "body": "完整正文",
                "expected_source_count": 2,
                "source_capture_complete": True,
                "sources": [
                    {"url": "javascript:bad"},
                    {"url": "https://example.com"},
                    {"url": "https://example.com"},
                ],
            }
        )
        result = cli.collect_one(fake, "deepseek", "问题")
        self.assertEqual(result["source_count"], 1)
        self.assertIs(result["source_capture_complete"], False)

    def test_explicitly_incomplete_zero_sources_remain_incomplete(self):
        fake = FakeCollector()
        fake.collect = Mock(
            return_value={
                "body": "完整正文",
                "sources": [],
                "source_capture_complete": False,
                "expected_source_count": 0,
            }
        )
        self.assertIs(
            cli.collect_one(fake, "deepseek", "问题")["source_capture_complete"], False
        )

    def test_javascript_exception_is_reported(self):
        page = CDPPage.__new__(CDPPage)
        page.call = Mock(return_value={"exceptionDetails": {"text": "ReferenceError"}})
        with self.assertRaisesRegex(RuntimeError, "ReferenceError"):
            page.evaluate("missing_function()")

    def test_scrapling_evaluation_is_not_replayed_after_context_loss(self):
        page = ScraplingStealthPage.__new__(ScraplingStealthPage)
        page.timeout_ms = 60000
        page.page = Mock()
        page.page.evaluate.side_effect = RuntimeError("execution context was destroyed")
        with self.assertRaises(RuntimeError):
            page.evaluate("side_effect()")
        page.page.evaluate.assert_called_once()

    def test_baidu_verification_is_not_ready(self):
        page = Mock()
        page.evaluate.return_value = {
            "url": "https://wappass.baidu.com",
            "title": "百度安全验证",
            "body": "请完成下方验证",
        }
        collector = WenxinWebCollector(page=page)
        self.addCleanup(collector.close)
        with self.assertRaisesRegex(RuntimeError, "未就绪"):
            collector.account_identity()

    def test_wenxin_final_body_must_finish_and_settle(self):
        page = Mock()
        body = "完成后的文心回答正文。" * 10
        page.evaluate.side_effect = [
            {"body": "未完成的正文。" * 10, "finished": False},
            {"body": body, "finished": True},
            {"body": body, "finished": True},
        ]
        collector = WenxinWebCollector(page=page)
        self.addCleanup(collector.close)
        with patch("wenxin_monitor.controller.time.sleep"):
            self.assertEqual(collector._settled_wenxin_snapshot()["body"], body)


if __name__ == "__main__":
    unittest.main()

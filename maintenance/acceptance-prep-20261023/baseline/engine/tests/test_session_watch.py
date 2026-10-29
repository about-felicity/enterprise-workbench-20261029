import contextlib
import io
import json
import os
import tempfile
import unittest
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

from geo_source_cards import cli, session_watch
from geo_source_cards.journal import Journal
from geo_source_cards.runtime import atomic_json, process_lock
from web_collectors.collector import BrowserCollector
from web_collectors.config import site_config


class SessionWatchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.now = [1000.0]
        self.notify = Mock()
        self.reporter = session_watch.SessionReporter(
            self.root, notify=self.notify, clock=lambda: self.now[0]
        )
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)
        env = patch.dict(os.environ, {"GEO_COLLECTOR_RUNTIME": str(self.root)})
        env.start()
        self.addCleanup(env.stop)

    def test_first_logout_notifies_and_persists_safe_status(self):
        state = self.reporter.publish(
            {
                "status": "login_required",
                "message": "请登录",
                "cookies": "MUST_NOT_SAVE",
            }
        )
        self.notify.assert_called_once()
        self.assertEqual(state["status"], "login_required")
        saved = (self.root / "deepseek_session.json").read_text(encoding="utf8")
        self.assertNotIn("MUST_NOT_SAVE", saved)
        events = (self.root / "deepseek_session_events.jsonl").read_text(
            encoding="utf8"
        )
        self.assertEqual(json.loads(events)["event"], "login_required")

    def test_reminder_is_deduplicated_across_process_restarts(self):
        self.reporter.publish({"status": "login_required"})
        self.now[0] += 180
        restarted = session_watch.SessionReporter(
            self.root, notify=self.notify, clock=lambda: self.now[0]
        )
        restarted.publish({"status": "login_required"})
        self.assertEqual(self.notify.call_count, 1)
        self.now[0] = 1900
        restarted.publish({"status": "login_required"})
        self.assertEqual(self.notify.call_count, 2)

    def test_unknown_does_not_claim_logout_or_recovery(self):
        self.reporter.publish({"status": "ready"})
        self.reporter.publish({"status": "unknown", "message": "网络异常"})
        self.notify.assert_not_called()

    def test_recovery_after_unknown_is_reported_once(self):
        self.reporter.publish({"status": "login_required"})
        self.reporter.publish({"status": "unknown"})
        self.reporter.publish({"status": "ready"})
        self.reporter.publish({"status": "ready"})
        self.assertEqual(self.notify.call_count, 2)
        self.assertEqual(self.notify.call_args.args[0], "ready")
        self.assertIsNone(
            json.loads(
                (self.root / "deepseek_session.json").read_text(encoding="utf8")
            )["login_required_since"]
        )

    def test_corrupt_status_recovers_without_treating_it_as_ready(self):
        (self.root / "deepseek_session.json").write_text("{broken")
        self.reporter.publish({"status": "unknown"})
        self.notify.assert_not_called()
        self.assertEqual(
            json.loads(
                (self.root / "deepseek_session.json").read_text(encoding="utf8")
            )["status"],
            "unknown",
        )

    def test_failed_notification_does_not_break_capture_monitoring(self):
        self.notify.side_effect = OSError("desktop unavailable")
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(
                self.reporter.publish({"status": "login_required"})["status"],
                "login_required",
            )

    def test_busy_collector_is_not_navigated_or_reopened(self):
        self.reporter.publish({"status": "ready"})
        before = (self.root / "deepseek_session.json").read_bytes()
        factory = Mock()
        with process_lock(self.root / "collector.lock"):
            result = session_watch.check_once(self.root, self.reporter, factory=factory)
        self.assertEqual(result["status"], "check_skipped")
        factory.assert_not_called()
        self.assertEqual((self.root / "deepseek_session.json").read_bytes(), before)

    def test_idle_check_closes_browser_and_releases_profile_lock(self):
        collector = Mock()
        collector.check_ready.return_value = {"status": "ready", "ok": True}
        result = session_watch.check_once(
            self.root, self.reporter, factory=Mock(return_value=collector)
        )
        self.assertEqual(result["status"], "ready")
        collector.close.assert_called_once()
        self.assertIs(collector.session_reporter, self.reporter)
        with process_lock(self.root / "collector.lock"):
            pass

    def test_browser_error_is_unknown_not_logout(self):
        result = session_watch.check_once(
            self.root, self.reporter, factory=Mock(side_effect=TimeoutError())
        )
        self.assertEqual(result["status"], "unknown")
        self.notify.assert_not_called()

    def test_browser_cleanup_failure_does_not_leave_profile_locked(self):
        collector = Mock()
        collector.check_ready.return_value = {"status": "ready"}
        collector.close.side_effect = OSError("close failed")
        session_watch.check_once(
            self.root, self.reporter, factory=Mock(return_value=collector)
        )
        self.assertEqual(
            json.loads(
                (self.root / "deepseek_session.json").read_text(encoding="utf8")
            )["status"],
            "unknown",
        )
        with process_lock(self.root / "collector.lock"):
            pass

    def test_watch_uses_configured_interval_and_stops_cleanly(self):
        stop = Mock(spec=Event)
        stop.is_set.return_value = False
        stop.wait.return_value = True
        with patch.object(
            session_watch, "check_once", return_value={"status": "ready"}
        ) as check:
            session_watch.watch(
                self.root, interval=180, reporter=self.reporter, stop=stop
            )
        check.assert_called_once()
        stop.wait.assert_called_once_with(180)

    def test_second_watcher_is_rejected(self):
        with process_lock(self.root / "deepseek_watch.lock"):
            with self.assertRaises(RuntimeError):
                session_watch.watch(self.root, stop=Event())

    def test_rate_wait_checks_session_every_three_minutes(self):
        path = self.root / "rate.json"
        atomic_json(path, {"last_prompt_epoch": 1000})
        sleeps = []

        def sleep(seconds):
            sleeps.append(seconds)
            self.now[0] += seconds

        check = Mock()
        cli.wait_for_deepseek_slot(
            path,
            min_interval=600,
            clock=lambda: self.now[0],
            sleep=sleep,
            check_session=check,
        )
        self.assertEqual(sleeps, [180, 180, 180, 60])
        self.assertEqual(check.call_count, 5)

    def test_loss_during_rate_wait_does_not_reserve_another_prompt(self):
        path = self.root / "rate.json"
        atomic_json(path, {"last_prompt_epoch": 1000})

        def sleep(seconds):
            self.now[0] += seconds

        check = Mock(side_effect=[None, session_watch.LoginRequiredError("请登录")])
        with self.assertRaises(session_watch.LoginRequiredError):
            cli.wait_for_deepseek_slot(
                path, clock=lambda: self.now[0], sleep=sleep, check_session=check
            )
        self.assertEqual(
            json.loads(path.read_text(encoding="utf8"))["last_prompt_epoch"], 1000
        )

    def test_logout_before_prompt_leaves_task_pending(self):
        args = cli.parse_args(
            ["--model", "deepseek", "--question", "测试", "--batch", "login-before"]
        )
        collector = Mock()
        collector.check_ready.return_value = {
            "ok": False,
            "status": "login_required",
            "message": "请登录",
        }
        with patch.object(cli, "create_collector", return_value=collector):
            with self.assertRaises(session_watch.LoginRequiredError):
                cli.run(args)
        collector.collect.assert_not_called()
        journal = Journal(self.root / "tasks.sqlite")
        self.addCleanup(journal.close)
        self.assertEqual(
            journal.db.execute("select state from captures").fetchone()[0], "pending"
        )

    def test_logout_after_submission_is_never_automatically_replayed(self):
        args = cli.parse_args(
            ["--model", "deepseek", "--question", "测试", "--batch", "login-after"]
        )
        collector = Mock()
        collector.assert_session = Mock()
        collector.check_ready.return_value = {"ok": True, "status": "ready"}
        collector.collect.side_effect = session_watch.LoginRequiredError("回答期间掉线")
        with patch.object(cli, "create_collector", return_value=collector):
            with self.assertRaises(session_watch.LoginRequiredError):
                cli.run(args)
        collector.collect.assert_called_once()
        with patch.object(cli, "create_collector") as factory:
            with self.assertRaisesRegex(RuntimeError, "uncertain"):
                cli.run(args)
            factory.assert_not_called()

    def test_passive_session_probe_raises_typed_logout_error(self):
        collector = BrowserCollector.__new__(BrowserCollector)
        collector.session_reporter = self.reporter
        collector.session_status = Mock(
            return_value={"ok": False, "status": "login_required", "message": "请登录"}
        )
        with self.assertRaises(session_watch.LoginRequiredError):
            collector.assert_session()
        self.notify.assert_called_once()

    def test_session_detector_distinguishes_ready_logout_and_unknown(self):
        collector = BrowserCollector.__new__(BrowserCollector)
        collector.site = site_config("deepseek")
        collector.page = Mock()
        for snapshot, expected in (
            ({"hostOk": True, "composer": True, "readyState": "complete"}, "ready"),
            (
                {"hostOk": True, "composer": True, "loginRequired": True},
                "login_required",
            ),
            ({"hostOk": True, "composer": False, "readyState": "complete"}, "unknown"),
        ):
            collector.page.evaluate.return_value = snapshot
            self.assertEqual(collector.session_status()["status"], expected)
        collector.page.call.assert_not_called()


if __name__ == "__main__":
    unittest.main()

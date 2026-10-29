import tempfile
import unittest
from pathlib import Path
from geo_source_cards.journal import Journal
from geo_source_cards.search_recovery import SearchRecovery, security_backoff_seconds


class RecoveryTests(unittest.TestCase):
    def test_optional_baidu_read_errors_end_after_two_without_erasing_history(self):
        task = self.j.plan('optional', 'baidu_ai', ['问题'], 1, self.root / 'baidu.jsonl')[0]
        recovery = SearchRecovery(self.j, self.root, clock=lambda: self.now, optional_baidu=True)
        self.j.start(task['task_id'])
        first = recovery.failure(task, RuntimeError('百度 AI 卡片未完整呈现'))
        self.assertFalse(first['exhausted'])
        self.j.start(task['task_id'])
        second = recovery.failure(task, RuntimeError('Source completeness is not proven'))
        self.assertTrue(second['exhausted'])
        self.assertEqual(second['attempt_limit'], 2)
        self.assertEqual(self.j.db.execute('select count(*) from search_recovery_attempts').fetchone()[0], 2)

    def test_optional_baidu_keeps_persistent_verification_gate(self):
        task = self.j.plan('optional', 'baidu_ai', ['问题'], 1, self.root / 'baidu.jsonl')[0]
        recovery = SearchRecovery(self.j, self.root, clock=lambda: self.now, optional_baidu=True)
        for _ in range(4):
            self.j.start(task['task_id'])
            result = recovery.failure(task, RuntimeError('百度安全验证'))
        self.assertEqual(result['status'], 'waiting_verification')
        self.assertTrue(recovery.control()['blocked'])

    def test_only_explicit_navigation_dns_failure_is_retryable(self):
        from geo_source_cards.search_recovery import classified
        self.assertEqual(classified("Page.goto: net::ERR_NAME_NOT_RESOLVED at https://chat.baidu.com/search"), "read_error")
        self.assertIsNone(classified("API POST timeout; submission unknown"))

    def test_network_changed_recovery_preserves_failed_task_evidence(self):
        error = 'Page.goto: net::ERR_NETWORK_CHANGED at https://www.baidu.com/'
        self.j.start(self.task['task_id'])
        self.j.fail(self.task['task_id'], error)
        result = self.r.failure(self.task, error)
        self.assertEqual(result['kind'], 'read_error')
        self.assertEqual(result['attempt'], 1)
        self.assertEqual(self.j.db.execute('select state from captures').fetchone()[0], 'pending')
        self.assertEqual(self.j.db.execute('select error from search_recovery_attempts').fetchone()[0], error)
        self.assertEqual(self.r.control()['cooldown_until'], self.now + 20)

    def test_network_change_never_retries_deepseek_or_unknown_submission(self):
        from geo_source_cards.search_recovery import classified
        self.j.start(self.task['task_id'])
        self.assertIsNone(classified('POST net::ERR_NETWORK_CHANGED; submission unknown'))
        self.assertIsNone(self.r.failure({**dict(self.task), 'model':'deepseek'},
            'Page.goto: net::ERR_NETWORK_CHANGED at https://chat.deepseek.com/'))

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.j = Journal(self.root / "tasks.sqlite")
        self.task = self.j.plan(
            "b", "wenxin_card", ["问题"], 1, self.root / "rows.jsonl"
        )[0]
        self.now = 1000
        self.r = SearchRecovery(self.j, self.root, clock=lambda: self.now)

    def tearDown(self):
        self.j.close()
        self.tmp.cleanup()

    def fail(self, error="百度安全验证"):
        self.j.start(self.task["task_id"])
        return self.r.failure(self.task, error)

    def test_backoff_cap_and_restart_persistence(self):
        self.assertEqual(
            [security_backoff_seconds(n) for n in range(1, 7)],
            [180, 360, 720, 900, 900, 900],
        )
        self.fail()
        second = SearchRecovery(self.j, self.root, clock=lambda: self.now)
        self.assertEqual(second.control()["cooldown_until"], 1180)
        self.assertEqual(second.control()["streak"], 1)

    def test_deferral_and_finite_cycles(self):
        values = [self.fail("Source completeness is not proven") for _ in range(8)]
        self.assertTrue(values[1]["defer"])
        self.assertTrue(values[-1]["exhausted"])
        self.assertEqual(
            self.j.db.execute("select state from captures").fetchone()[0],
            "failed_deferred",
        )

    def test_persistent_verification_requires_operator(self):
        for _ in range(4):
            result = self.fail()
        self.assertEqual(result["status"], "waiting_verification")
        with self.assertRaisesRegex(RuntimeError, "等待人工"):
            SearchRecovery(self.j, self.root).wait(None)

    def test_success_resets_shared_streak_not_attempt_history(self):
        self.fail()
        self.r.success()
        self.assertEqual(self.r.control()["streak"], 0)
        self.assertEqual(
            self.j.db.execute(
                "select count(*) from search_recovery_attempts"
            ).fetchone()[0],
            1,
        )

    def test_unknown_and_deepseek_not_retried(self):
        self.j.start(self.task["task_id"])
        self.assertIsNone(
            self.r.failure(
                self.task, "Previous capture interrupted; submission outcome unknown"
            )
        )
        self.assertIsNone(
            self.r.failure({**dict(self.task), "model": "deepseek"}, "百度安全验证")
        )
        self.assertEqual(
            self.j.db.execute(
                "select count(*) from search_recovery_attempts"
            ).fetchone()[0],
            0,
        )

    def test_completed_result_cannot_be_reset(self):
        self.j.start(self.task["task_id"])
        self.j.complete(self.task["task_id"], {"body": "saved"})
        with self.assertRaises(RuntimeError):
            self.r.failure(self.task, "百度安全验证")

    def test_baidu_limit_is_twenty_attempts(self):
        task = self.j.plan("c", "baidu_ai", ["其他"], 1, self.root / "baidu.jsonl")[0]
        for n in range(20):
            self.j.start(task["task_id"])
            result = self.r.failure(task, "百度 AI 卡片未完整呈现")
            self.assertEqual(result["exhausted"], n == 19)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from geo_source_cards.acceptance import advance, prerequisites


class AcceptanceTests(unittest.TestCase):
    def test_waiting_time_never_counts_as_observation(self):
        waiting = advance({}, 100, ["capture incomplete"])
        later = advance(waiting, 30000, ["capture incomplete"])
        self.assertEqual(later["status"], "waiting_prerequisites")
        self.assertEqual(later["elapsed_seconds"], 0)
        self.assertEqual(advance(later, 30060, [])["started_epoch"], 30060)

    def test_six_hours_requires_continuous_successful_observations(self):
        state = advance({}, 1000, [])
        for now in range(1060, 22601, 60):
            state = advance(state, now, [])
        self.assertEqual(state["status"], "passed")
        self.assertEqual(state["elapsed_seconds"], 21600)

    def test_failure_is_latched_and_cannot_restart_itself(self):
        running = advance({}, 1000, [])
        failed = advance(running, 1060, ["login expired"])
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(advance(failed, 30000, []), failed)

    def test_gap_and_clock_rollback_fail_observation(self):
        running = advance({}, 1000, [])
        self.assertEqual(advance(running, 1181, [])["status"], "failed")
        self.assertEqual(advance(running, 999, [])["status"], "failed")

    def test_missing_capture_and_local_receipt_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "questions.txt").write_text("原始问题", encoding="utf8")
            reasons = prerequisites(root, "2026-10-08", 1000, {})
            self.assertTrue(any("deepseek" in reason for reason in reasons))
            self.assertTrue(any("baidu_ai" in reason for reason in reasons))
            self.assertTrue(any("wenxin_card" in reason for reason in reasons))
            self.assertTrue(any("本地成品" in reason for reason in reasons))
            self.assertTrue(any("Word" in reason for reason in reasons))


if __name__ == "__main__":
    unittest.main()

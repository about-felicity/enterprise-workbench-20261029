import copy
import unittest
import tempfile
from pathlib import Path
from datetime import datetime
from . import observation as o


class ObservationTests(unittest.TestCase):
    def test_nested_logic_request_states_are_observed(self):
        with tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            names=['quality-repair/batch/item/attempt-1/calls/review/logic-call/api_state.json','logic-review/day/item/call/api_state.json','logic-revision/day/calls/review/logic-call/api_state.json','runs/job/api/runs/review/call/logic-call/api_state.json','runs/job/api/runs/review/logic-call/api_state.json']
            for name in names:
                path=base/'runtime'/name;path.parent.mkdir(parents=True);path.write_text('{}')
            self.assertEqual(set(o.request_state_paths(base)),{base/'runtime'/name for name in names})

    def setUp(self):
        self.base = {'services': {'worker': 'active'}, 'expected_writing_plans': ['p'], 'expected_geo_models': ['doubao1'], 'next_day_jobs': {}, 'next_day_tasks': {}, 'job_states': [], 'protected_controls': {'paused': 'sha'}, 'ledger': {'unresolved': 3, 'total_committed': 4}, 'unknown_request_ids': ['old'], 'daily_budget_cny': 10, 'geo_counts': []}

    def test_success_cannot_be_claimed_before_real_window_ends(self):
        result = o.evaluate(self.base, self.base, datetime(2026, 10, 21, 15, tzinfo=o.ZONE))
        self.assertEqual(result['state'], 'observing')
        self.assertFalse(result['cross_day_passed'])

    def test_missing_real_work_fails_at_end(self):
        self.assertEqual(o.evaluate(self.base, self.base, o.END)['state'], 'needs_attention')

    def test_duplicate_unknown_and_modified_pause_are_detected(self):
        s = copy.deepcopy(self.base)
        s['next_day_jobs'] = {'p': [{'date': '2026-10-22', 'question': 'q', 'day_status': 'complete'}] * 2}
        s['unknown_request_ids'].append('new')
        s['protected_controls'] = {}
        issues = o.evaluate(s, self.base, o.END)['issues']
        self.assertIn('duplicate_job:p', issues)
        self.assertIn('new_unresolved_api_request', issues)
        self.assertIn('paused_control_changed:paused', issues)

    def test_active_reservation_does_not_count_as_unknown_delivery(self):
        s = copy.deepcopy(self.base)
        s['ledger']['unresolved'] = 4
        self.assertNotIn('new_unresolved_api_request', o.evaluate(s, self.base, datetime(2026, 10, 21, 16, tzinfo=o.ZONE))['issues'])

    def test_only_complete_real_jobs_and_geo_can_pass(self):
        s = copy.deepcopy(self.base)
        s['next_day_jobs'] = {'p': [{'date': '2026-10-22', 'question': 'q', 'day_status': 'complete'}]}
        s['geo_counts'] = [{'model': 'doubao1', 'target': 105, 'credited_pg': 105}]
        s['observed_dates'] = ['2026-10-21', '2026-10-22']
        self.assertTrue(o.evaluate(s, self.base, o.END)['cross_day_passed'])

    def test_source_edits_or_observation_gaps_prevent_unattended_claim(self):
        s = copy.deepcopy(self.base)
        s.update(source_fingerprint='changed', observation_max_gap_seconds=2400)
        baseline = {**self.base, 'source_fingerprint': 'original'}
        issues = o.evaluate(s, baseline, o.END)['issues']
        self.assertIn('source_changed_during_observation', issues)
        self.assertIn('observation_gap_over_35_minutes', issues)


if __name__ == '__main__':
    unittest.main()

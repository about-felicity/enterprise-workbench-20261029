import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from . import repair_followup as followup, runtime


class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.item = {'key': 'a', 'root': str(self.base / 'job'), 'id': '2026-10-20/排行类/01', 'writer': str(self.base / 'writer'), 'original_word_sha256': 'original'}
        self.root_patch = patch.object(followup.repair, 'ROOT', self.base / 'repairs')
        self.root_patch.start()
        runtime.atomic_json(followup.repair.ROOT / 'a/status.json', {'state': 'needs_attention', 'reason': 'consumer_contract_maintenance'})
        runtime.atomic_json(self.base / 'job/approved' / self.item['id'] / 'receipt.json', {'word_sha256': 'original'})
        self.material = patch.object(followup, 'require_writer_material')
        self.material.start()
        self.evidence = patch.object(followup, 'evidence_units', return_value=[])
        self.evidence.start()

    def tearDown(self):
        self.evidence.stop()
        self.material.stop()
        self.root_patch.stop()
        self.tmp.cleanup()

    def test_only_unsent_unpaused_unchanged_article_is_eligible(self):
        self.assertIsNone(followup.eligibility(self.item))
        runtime.atomic_json(self.base / 'job/control.json', {'paused': True, 'reason': 'operator'})
        self.assertEqual(followup.eligibility(self.item), 'production_job_paused')

    def test_maintenance_label_cannot_hide_existing_send(self):
        runtime.atomic_json(followup.repair.ROOT / 'a/attempt-2/calls/writer/api_state.json', {'state': 'REQUEST_UNKNOWN'})
        self.assertEqual(followup.eligibility(self.item), 'existing_request_evidence')

    def test_changed_version_and_active_execution_are_excluded(self):
        runtime.atomic_json(self.base / 'job/approved' / self.item['id'] / 'receipt.json', {'word_sha256': 'new'})
        self.assertEqual(followup.eligibility(self.item), 'article_version_changed')
        runtime.atomic_json(self.base / 'job/approved' / self.item['id'] / 'receipt.json', {'word_sha256': 'original'})
        runtime.atomic_json(self.base / 'job/api/active.json', {'state': 'REQUESTING'})
        self.assertEqual(followup.eligibility(self.item), 'production_execution_in_progress')

    def test_unknown_status_is_never_selected(self):
        runtime.atomic_json(followup.repair.ROOT / 'a/status.json', {'state': 'unknown_request', 'reason': 'network_delivery_unknown'})
        self.assertEqual(followup.eligibility(self.item), 'not_unsent_maintenance_hold')

    def test_explicit_isolated_repair_keeps_original_job_paused(self):
        path = self.base / 'job/control.json'
        runtime.atomic_json(path, {'paused': True, 'reason': 'operator', 'revision': 4})
        before = path.read_bytes()
        self.assertIsNone(followup.eligibility(self.item, include_paused_sources=True))
        self.assertEqual(path.read_bytes(), before)
        runtime.atomic_json(followup.repair.ROOT / 'a/attempt-3/calls/writer/request.json', {'model': 'example'})
        self.assertEqual(followup.eligibility(self.item, include_paused_sources=True), 'existing_request_evidence')


if __name__ == '__main__':
    unittest.main()

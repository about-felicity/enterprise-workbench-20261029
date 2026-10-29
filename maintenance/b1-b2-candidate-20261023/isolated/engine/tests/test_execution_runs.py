import tempfile
import unittest
from pathlib import Path

from geo_source_cards.execution_runs import authorize, verify_execution
from geo_source_cards.runtime import atomic_json


class ExecutionRunTests(unittest.TestCase):
    def test_authorization_is_idempotent_but_cannot_replace_unknown_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ticket, client, run = "a" * 24, "b" * 24, "c" * 24
            atomic_json(
                root / "queue" / ticket / "ticket.json",
                {"state": "claimed", "client": client},
            )
            job = authorize(root, ticket, client, run)
            self.assertEqual(authorize(root, ticket, client, run), job)
            with self.assertRaises(ValueError):
                authorize(root, ticket, client, "d" * 24)
            with self.assertRaises(ValueError):
                authorize(root, ticket, "e" * 24, run)

    def test_old_generation_and_missing_execution_are_rejected(self):
        job = {"execution": {"run_id": "a" * 24, "generation": 2}}
        with self.assertRaises(ValueError):
            verify_execution(job, {"execution": {"run_id": "a" * 24, "generation": 1}})
        with self.assertRaises(ValueError):
            verify_execution(job, {})
        verify_execution(job, {"execution": job["execution"]})
        verify_execution({}, {})

    def test_existing_delivery_cannot_be_overwritten_by_a_new_run(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ticket, client = "a" * 24, "b" * 24
            folder = root / "queue" / ticket
            atomic_json(folder / "ticket.json", {"state": "claimed", "client": client})
            atomic_json(folder / "receipt.json", {"state": "completed"})
            with self.assertRaises(ValueError):
                authorize(root, ticket, client, "c" * 24)

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import requests

from geo_source_cards.deepseek_api import APIError, DeepSeekClient


class APIDurabilityTests(unittest.TestCase):
    def test_article_budget_rejection_is_unsent_and_does_not_pause_other_articles(self):
        from geo_source_cards.api_budget import ArticleBudgetExceeded
        self.client.budget=Mock(root=self.root)
        self.client.budget.reserve.side_effect=ArticleBudgetExceeded('local cap')
        self.client.balance=Mock(return_value={'is_available':True})
        with self.assertRaisesRegex(APIError,'article_budget_exceeded'):
            self.client.complete('task',self.root/'run')
        self.session.post.assert_not_called()
        self.assertFalse((self.root/'control.json').exists())
        self.assertFalse((self.root/'run/api_state.json').exists())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.secret = "sk-" + "s" * 32
        key = self.root / "key"
        key.write_text(self.secret, encoding="utf8")
        self.session = Mock()
        self.session.post.return_value.status_code = 200
        self.session.post.return_value.json.return_value = {
            "choices": [
                {"finish_reason": "stop", "message": {"content": '{"ok":true}'}}
            ],
            "model": "deepseek-flash",
        }
        self.client = DeepSeekClient(key, session=self.session)

    def test_cached_response_does_not_repeat_request_and_is_bound_to_prompt(self):
        run = self.root / "run"
        self.assertEqual(self.client.complete("task", run), {"ok": True})
        self.assertEqual(self.client.complete("task", run), {"ok": True})
        with self.assertRaisesRegex(APIError, "input_mismatch"):
            self.client.complete("changed", run)
        self.assertEqual(self.session.post.call_count, 1)
        for path in run.glob("*.json"):
            self.assertNotIn(self.secret, path.read_text("utf8"))
        payload = self.session.post.call_args.kwargs["json"]
        self.assertEqual(payload["model"], "deepseek-flash")
        self.assertFalse(self.session.post.call_args.kwargs["allow_redirects"])

    def test_unknown_network_delivery_never_retries(self):
        self.session.post.side_effect = requests.Timeout("sensitive provider message")
        run = self.root / "run"
        with self.assertRaises(APIError) as context:
            self.client.complete("task", run)
        self.assertTrue(context.exception.uncertain)
        with self.assertRaisesRegex(APIError, "reconciliation"):
            self.client.complete("task", run)
        self.assertEqual(self.session.post.call_count, 1)
        self.assertNotIn("sensitive", (run / "api_state.json").read_text("utf8"))

    def test_review_keeps_output_budget_for_structured_answer(self):
        self.client.complete(
            "review evidence", self.root / "review", stage="review", max_tokens=3500
        )
        payload = self.session.post.call_args.kwargs["json"]
        self.assertEqual(payload["thinking"], {"type": "disabled"})
        self.assertNotIn("reasoning_effort", payload)
        self.assertEqual(payload["max_tokens"], 3500)

    def test_truncated_generation_is_never_success(self):
        self.session.post.return_value.json.return_value["choices"][0][
            "finish_reason"
        ] = "length"
        run = self.root / "run"
        with self.assertRaisesRegex(APIError, "output_incomplete"):
            self.client.complete("task", run)
        self.assertFalse((run / "response.json").exists())
        self.assertEqual(
            json.loads((run / "api_state.json").read_text("utf8"))["state"],
            "INVALID_RESPONSE",
        )

    def test_http_failure_does_not_expose_response_or_retry(self):
        self.session.post.return_value.status_code = 401
        run = self.root / "run"
        with self.assertRaisesRegex(APIError, "http_401"):
            self.client.complete("task", run)
        with self.assertRaises(APIError):
            self.client.complete("task", run)
        self.assertEqual(self.session.post.call_count, 1)

    def test_orphan_response_cannot_be_used(self):
        run = self.root / "run"
        run.mkdir()
        (run / "response.json").write_text('{"ok":true}', encoding="utf8")
        with self.assertRaisesRegex(APIError, "orphan"):
            self.client.complete("task", run)
        self.session.post.assert_not_called()

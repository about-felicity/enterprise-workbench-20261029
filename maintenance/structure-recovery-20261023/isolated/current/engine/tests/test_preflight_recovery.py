import unittest
from unittest.mock import Mock, patch

from web_collectors.collector import BrowserCollector, PreSubmissionPageError


class PreflightRecoveryTests(unittest.TestCase):
    def collector(self):
        collector = BrowserCollector.__new__(BrowserCollector)
        collector.has_session_cookies = True
        collector.navigate_home = Mock()
        collector.session_reporter = Mock()
        return collector

    def test_loading_page_recovers_before_submission(self):
        collector = self.collector()
        unknown = {"ok": False, "status": "unknown"}
        ready = {"ok": True, "status": "ready"}
        collector.session_status = Mock(side_effect=[unknown, ready])
        with patch('web_collectors.collector.time.monotonic', side_effect=[0, 1, 21, 22, 23]), patch('web_collectors.collector.time.sleep'):
            self.assertEqual(collector.check_ready(), ready)
        self.assertEqual(collector.navigate_home.call_count, 2)

    def test_login_gate_is_not_retried(self):
        collector = self.collector()
        collector.session_status = Mock(return_value={"ok": False, "status": "login_required"})
        self.assertEqual(collector.check_ready()["status"], "login_required")
        collector.navigate_home.assert_called_once()

    def test_persistent_unknown_has_bounded_attempts(self):
        collector = self.collector()
        collector.session_status = Mock(return_value={"ok": False, "status": "unknown"})
        with patch('web_collectors.collector.time.monotonic', side_effect=[0,1,21,22,23,43,44,45,65]), patch('web_collectors.collector.time.sleep'):
            self.assertFalse(collector.check_ready()['ok'])
        self.assertEqual(collector.navigate_home.call_count, 3)

    def test_failed_preflight_never_submits(self):
        collector = self.collector()
        collector.check_ready = Mock(return_value={"ok": False, "status": "unknown"})
        collector._submit = Mock()
        with self.assertRaises(PreSubmissionPageError):
            collector.collect('test')
        collector._submit.assert_not_called()
        self.assertFalse(collector.submission_started)

    def test_send_requires_receipt_and_clicks_once(self):
        collector = self.collector()
        collector.page = Mock()
        collector.assert_session = Mock()
        collector._input_state = Mock(return_value={'ok': True})
        collector._save_failure_evidence = Mock()
        collector._send_state = Mock(side_effect=[
            {'text': 'question', 'button': {'x': 10, 'y': 20}},
            {'text': 'question', 'button': {'x': 10, 'y': 20}},
            {'url': 'https://chat.deepseek.com/a/chat/s/test', 'text': '', 'conversationText': 'question'},
        ])
        collector._submit('question')
        collector.page.click.assert_called_once_with(10, 20)

    def test_unknown_receipt_does_not_click_twice(self):
        collector = self.collector()
        collector.page = Mock()
        collector.assert_session = Mock()
        collector._input_state = Mock(return_value={'ok': True})
        collector._save_failure_evidence = Mock()
        collector._send_state = Mock(return_value={'text': 'question', 'button': {'x': 10, 'y': 20}})
        with patch('web_collectors.collector.time.monotonic', side_effect=[0,1,2,3,100]), patch('web_collectors.collector.time.sleep'):
            with self.assertRaisesRegex(RuntimeError, '禁止自动重发'):
                collector._submit('question')
        collector.page.click.assert_called_once()
        self.assertEqual([call.args[1] for call in collector._save_failure_evidence.call_args_list],
                         ['before_single_send_click','submission_unconfirmed'])

    def test_answer_timeout_refreshes_original_conversation_once(self):
        collector = self.collector()
        collector.page = Mock()
        collector._submit = Mock()
        collector._save_failure_evidence = Mock()
        result = {'url': 'https://chat.deepseek.com/a/chat/s/original', 'body': 'answer'}
        collector._send_state = Mock(return_value={**result, 'conversationText': 'question'})
        collector._wait_current_answer = Mock(side_effect=[TimeoutError(), result])
        with patch('web_collectors.collector.time.sleep'):
            self.assertEqual(collector._wait_answer_with_refresh('question'), result)
        collector.page.call.assert_called_once_with('Page.reload', {}, timeout=30)
        collector._submit.assert_not_called()

    def test_refresh_is_bounded_and_cannot_change_conversations(self):
        for failure in (TimeoutError(), {'url': 'https://chat.deepseek.com/a/chat/s/other'}):
            collector = self.collector()
            collector.page = Mock()
            collector._save_failure_evidence = Mock()
            collector._send_state = Mock(return_value={'url':'https://chat.deepseek.com/a/chat/s/original','conversationText':'question'})
            collector._wait_current_answer = Mock(side_effect=[TimeoutError(), failure])
            with patch('web_collectors.collector.time.sleep'), self.assertRaises((TimeoutError, RuntimeError)):
                collector._wait_answer_with_refresh('question')
            self.assertEqual(collector.page.call.call_count, 1)

    def test_unknown_submission_is_not_refreshed(self):
        collector = self.collector()
        collector.page = Mock()
        collector._wait_current_answer = Mock(side_effect=TimeoutError())
        collector._send_state = Mock(return_value={'url': 'https://chat.deepseek.com/'})
        with self.assertRaises(TimeoutError):
            collector._wait_answer_with_refresh('question')
        collector.page.call.assert_not_called()

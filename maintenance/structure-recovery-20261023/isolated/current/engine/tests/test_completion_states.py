import unittest
from unittest.mock import Mock,patch
from web_collectors.collector import BrowserCollector
from web_collectors.config import site_config


class CompletionStateTests(unittest.TestCase):
    def collector(self):
        collector=BrowserCollector.__new__(BrowserCollector)
        collector.site=site_config('deepseek');collector.page=Mock()
        collector.page.evaluate.return_value='问题'
        collector._probe_session_if_due=Mock();collector._save_failure_evidence=Mock()
        collector._snapshot=Mock()
        return collector

    def test_short_body_is_complete_only_after_not_busy_and_stable(self):
        c=self.collector();now=[0]
        c._snapshot=Mock(side_effect=[{'body':'是。','busy':True,'readyState':'complete'},
                                     {'body':'是。','busy':False,'readyState':'complete'},
                                     {'body':'是。','busy':False,'readyState':'complete'}])
        def sleep(_):now[0]+=3
        with patch('web_collectors.collector.time.monotonic',side_effect=lambda:now[0]),patch('web_collectors.collector.time.sleep',side_effect=sleep):
            result=c._wait_current_answer('问题',timeout=30,stable_seconds=2)
        self.assertEqual(result['body'],'是。');self.assertEqual(c._snapshot.call_count,3)
        c.page.click.assert_not_called()

    def test_stuck_generation_times_out_and_keeps_original_evidence(self):
        c=self.collector();now=[0]
        c._snapshot.return_value={'body':'还在生成的正文','busy':True,'readyState':'complete'}
        def sleep(_):now[0]+=10
        with patch('web_collectors.collector.time.monotonic',side_effect=lambda:now[0]),patch('web_collectors.collector.time.sleep',side_effect=sleep):
            with self.assertRaises(TimeoutError):c._wait_current_answer('问题',timeout=30,stable_seconds=2)
        c._save_failure_evidence.assert_called_once();c.page.click.assert_not_called()

    def test_short_final_paragraph_is_not_rejected_by_body_length(self):
        c=self.collector()
        result=c._capture_result({'body':'是。','sources':[]},'问题')
        self.assertEqual(result['body'],'是。')
        self.assertIsNone(result['source_capture_complete'])

if __name__=='__main__':unittest.main()

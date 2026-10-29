import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from geo_source_cards import cli
class Tests(unittest.TestCase):
    def test_pause_during_rate_wait_never_reaches_submission_or_moves_fence(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'rate.json';marker=Path(tmp)/'pause.json';path.write_text(json.dumps({'last_search_epoch':100}))
            now=[101]
            def sleep(seconds):
                self.assertLessEqual(seconds,3);now[0]+=seconds;marker.write_text('{}')
            with patch.dict(os.environ,{'GEO_CAPTURE_PAUSE_FILE':str(marker)}):
                with self.assertRaises(cli.CaptureDrainRequested):cli.wait_for_search_slot(path,60,clock=lambda:now[0],sleep=sleep)
            self.assertEqual(json.loads(path.read_text())['last_search_epoch'],100)
    def test_completion_timestamp_fences_next_reservation_and_keeps_pure_question(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'rate.json'
            with patch.object(cli,'collect_one',return_value={'body':'full'}) as collect,patch.object(cli.time,'time',return_value=100):
                cli.collect_with_completion_fence(Mock(),'baidu_ai','纯问题',path)
            self.assertEqual(collect.call_args.args[2],'纯问题')
            self.assertEqual(json.loads(path.read_text())['last_search_epoch'],100)
            now=[101]
            def sleep(seconds):now[0]+=seconds
            cli.wait_for_search_slot(path,60,clock=lambda:now[0],sleep=sleep)
            self.assertEqual(now[0],160)
    def test_failure_also_fences_without_retrying(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'rate.json'
            with patch.object(cli,'collect_one',side_effect=RuntimeError('unknown')) as collect,patch.object(cli.time,'time',return_value=100):
                with self.assertRaises(RuntimeError):cli.collect_with_completion_fence(Mock(),'deepseek','纯问题',path)
            self.assertEqual(collect.call_count,1)
            self.assertEqual(json.loads(path.read_text())['last_prompt_epoch'],100)
if __name__=='__main__':unittest.main()

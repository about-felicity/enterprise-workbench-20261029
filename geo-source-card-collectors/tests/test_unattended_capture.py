import json
from contextlib import closing
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock,patch
from geo_source_cards import cli
from geo_source_cards.journal import Journal
from geo_source_cards.search_recovery import SearchRecovery


class UnattendedCaptureTests(unittest.TestCase):
    def test_missing_first_card_does_not_starve_later_question(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'GEO_UNATTENDED': '1'}):
            root=Path(tmp);questions=root/'questions.txt';questions.write_text('first\nsecond\n')
            args=cli.parse_args(['--model','baidu_ai','--runtime-dir',str(root),'--batch','fair',
                '--questions-file',str(questions),'--min-search-interval','0',
                '--bounded-search-recovery','--max-new-captures','1'])
            collector=Mock()
            present={'capture_mode':'baidu_search_ai','body':'完整且不同的卡片正文',
                'sources':[{'title':'来源','url':'https://source.test'}],
                'source_capture_complete':True,'body_capture_complete':True}
            with patch.object(cli,'create_collector',return_value=collector), patch.object(cli,'collect_one',
                side_effect=[RuntimeError('百度 AI 卡片未完整呈现'),cli.normalize_result(present,'baidu_ai','second')]) as collect, patch('geo_source_cards.search_recovery.SearchRecovery.evidence'):
                self.assertEqual(cli.run(args),75)
                with closing(Journal(root/'tasks.sqlite').db) as db:
                    db.execute('update search_recovery_control set cooldown_until=0');db.commit()
                self.assertEqual(cli.run(args),0)
                self.assertEqual([c.args[2] for c in collect.call_args_list],['first','second'])
            with closing(Journal(root/'tasks.sqlite').db) as db:
                self.assertEqual([tuple(r) for r in db.execute('select question,state from captures order by ordinal')],
                    [('first','pending'),('second','completed')])
                self.assertEqual(db.execute('select count(*) from search_recovery_attempts').fetchone()[0],1)

    def test_single_question_search_releases_lane_without_resending_during_cooldown(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {'GEO_UNATTENDED': '1'}):
            root = Path(tmp)
            args = cli.parse_args(['--model', 'baidu_ai', '--runtime-dir', str(root), '--batch', 'release',
                '--question', 'q', '--min-search-interval', '0', '--bounded-search-recovery', '--max-new-captures', '1'])
            collector = Mock()
            with patch.object(cli, 'create_collector', return_value=collector) as create, patch.object(cli, 'collect_one', side_effect=RuntimeError('百度 AI 卡片未完整呈现')) as collect, patch('geo_source_cards.search_recovery.SearchRecovery.evidence'):
                self.assertEqual(cli.run(args), 75)
                self.assertEqual(cli.run(args), 75)
                self.assertEqual(create.call_count, 1)
                self.assertEqual(collect.call_count, 1)
            collector.close.assert_called_once()
            with closing(Journal(root/'tasks.sqlite').db) as db:
                self.assertEqual(db.execute('select state from captures').fetchone()[0], 'pending')
                self.assertEqual(db.execute('select count(*) from search_recovery_attempts').fetchone()[0], 1)

    def test_daily_baidu_absence_stays_unfinished_until_real_card_is_read(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GEO_UNATTENDED':'1'}):
            root=Path(tmp)
            args=cli.parse_args(['--model','baidu_ai','--runtime-dir',str(root),'--batch','b',
                                 '--question','q','--rounds','1','--min-search-interval','0'])
            collector=Mock()
            absent={'capture_mode':'baidu_search_ai','availability':'no_card','body':'','sources':[],
                    'source_capture_complete':True,'body_capture_complete':True,
                    'absence_evidence':{'url':'https://www.baidu.com/s?wd=q','query':'q',
                                       'readyState':'complete','cardPresent':False,'searchResultsCount':3}}
            present={'capture_mode':'baidu_search_ai','body':'真实完整的卡片正文',
                     'sources':[{'title':'原来源','url':'https://source.test'}],
                     'source_capture_complete':True,'body_capture_complete':True}
            collector.collect_search.side_effect=[absent,present]
            with patch.object(cli,'create_collector',return_value=collector):
                with self.assertRaisesRegex(RuntimeError,'Daily Baidu card is still missing'):cli.run(args)
                with closing(Journal(root/'tasks.sqlite').db) as db:
                    self.assertNotEqual(db.execute('select state from captures').fetchone()[0],'completed')
                self.assertEqual(cli.run(args),0)
            with closing(Journal(root/'tasks.sqlite').db) as db:
                self.assertEqual(db.execute('select state from captures').fetchone()[0],'completed')
            self.assertEqual(collector.collect_search.call_count,2)

    def test_real_deepseek_readback_finalizes_body_and_sources_without_submission(self):
        from web_collectors.collector import BrowserCollector
        collector=object.__new__(BrowserCollector)
        collector.page=Mock()
        collector._submit=Mock(side_effect=AssertionError('Readback must never send'))
        url='https://chat.deepseek.com/a/chat/s/original'
        snapshot={'body':'完整的原始答案正文','url':url,'busy':False,
                  'sources':[{'title':'原始来源','url':'https://source.test/original'}]}
        collector._wait_answer_with_refresh=Mock(return_value=snapshot)
        collector._expand_source_panel=Mock(return_value=1)
        collector._snapshot=Mock(return_value=dict(snapshot))
        collector._probe_session_if_due=Mock()
        collector.session_reporter=Mock()
        collector.session_status=Mock(side_effect=[{'ok':False,'status':'unknown'}, {'ok':True,'status':'ready'}])
        with patch('web_collectors.collector.time.sleep'):
            result=collector.resume('原始问题',url,stable_seconds=0)
        self.assertEqual(result['wire_question'],'原始问题')
        self.assertEqual(result['body'],snapshot['body'])
        self.assertEqual(result['sources'],snapshot['sources'])
        self.assertTrue(result['source_capture_complete'])
        self.assertTrue(result['body_capture_complete'])
        self.assertEqual(collector.session_status.call_count,2)
        collector._submit.assert_not_called()

    def test_search_keeps_retrying_after_old_limit_without_erasing_attempts(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GEO_UNATTENDED':'1'}):
            root=Path(tmp);journal=Journal(root/'tasks.sqlite')
            try:
                task=journal.plan('b','baidu_ai',['q'],1,root/'results.jsonl')[0]
                recovery=SearchRecovery(journal,root,optional_baidu=True)
                for _ in range(25):
                    journal.start(task['task_id'])
                    result=recovery.failure(task,TimeoutError('transport'))
                    self.assertFalse(result['exhausted'])
                self.assertEqual(journal.db.execute('select count(*) from search_recovery_attempts').fetchone()[0],25)
            finally:journal.close()

    def test_durable_no_click_can_recover_but_attempted_click_cannot_be_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);journal=Journal(root/'tasks.sqlite')
            try:
                task=journal.plan('b','deepseek',['q'],1,root/'results.jsonl')[0]
                journal.start(task['task_id'],submission=True)
                journal.fail(task['task_id'],'before-click timeout')
                journal.automatic_recovery('b')
                self.assertEqual(journal.db.execute('select state from captures').fetchone()[0],'pending')
                journal.start(task['task_id'],submission=True)
                journal.submission(task['task_id'],{},attempted=True)
                journal.fail(task['task_id'],'response lost')
                journal.automatic_recovery('b')
                self.assertEqual(journal.db.execute('select state from captures').fetchone()[0],'needs_attention')
            finally:journal.close()

    def test_deepseek_after_send_timeout_resumes_only_original_conversation(self):
        with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GEO_UNATTENDED':'1'}):
            root=Path(tmp)
            args=cli.parse_args(['--model','deepseek','--runtime-dir',str(root),'--batch','b','--question','q','--rounds','1'])
            collector=Mock();collector.check_ready.return_value={'ok':True}
            collector.assert_session=Mock()
            url='https://chat.deepseek.com/a/chat/s/original'
            def send(*a,**kw):
                collector.submission_started=True
                collector.on_send_intent({'url':'https://chat.deepseek.com/'})
                collector.on_send_receipt({'url':url})
                raise TimeoutError('read interrupted after send')
            collector.collect.side_effect=send
            collector.resume.return_value={'body':'完整正文','sources':[{'title':'来源','url':'https://source.test'}],
                'source_capture_complete':True,'body_capture_complete':True,'capture_mode':'deepseek_web',
                'url':url,'wire_question':'q','expected_source_count':1}
            with patch.object(cli,'create_collector',return_value=collector):
                with self.assertRaises(TimeoutError):cli.run(args)
                self.assertEqual(cli.run(args),0)
            collector.collect.assert_called_once()
            collector.resume.assert_called_once_with('q',url)
            with closing(Journal(root/'tasks.sqlite').db) as db:
                self.assertEqual(db.execute('select state from captures').fetchone()[0],'completed')


if __name__=='__main__':unittest.main()

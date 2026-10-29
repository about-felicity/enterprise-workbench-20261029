import json,os,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
from geo_source_cards import cli
from geo_source_cards.journal import Journal

class SearchBrowserYieldTests(unittest.TestCase):
 def test_failed_search_yields_without_completing_and_next_lease_selects_unattempted_task(self):
  with tempfile.TemporaryDirectory() as tmp,patch.dict(os.environ,{'GEO_UNATTENDED':'1'}):
   root=Path(tmp);args=cli.parse_args(['--model','baidu_ai','--runtime-dir',str(root),'--batch','b','--question','q','--rounds','2','--min-search-interval','0','--bounded-search-recovery','--max-search-attempts','1'])
   c=Mock();c.collect_search.side_effect=RuntimeError('百度 AI 卡片未完整呈现')
   with patch.object(cli,'create_collector',return_value=c),patch('geo_source_cards.search_recovery.SearchRecovery.wait'):
    self.assertEqual(cli.run(args),0)
    journal=Journal(root/'tasks.sqlite')
    first=[dict(r) for r in journal.db.execute('select * from captures order by round')];journal.close()
    self.assertEqual(first[0]['state'],'pending');self.assertIsNotNone(first[0]['started']);self.assertIsNone(first[1]['started'])
    self.assertEqual(cli.run(args),0)
   journal=Journal(root/'tasks.sqlite')
   self.assertEqual(journal.db.execute("select count(*) from captures where state='completed'").fetchone()[0],0)
   self.assertEqual(journal.db.execute('select count(distinct task_id) from search_recovery_attempts').fetchone()[0],2);journal.close()
   self.assertEqual(c.collect_search.call_count,2)
   self.assertEqual(json.loads((root/'capture_progress.json').read_text())['phase'],'yielding_search_browser') if (root/'capture_progress.json').exists() else None
 def test_browser_lease_option_is_not_allowed_for_chat_submission(self):
  with self.assertRaises(SystemExit):cli.parse_args(['--model','deepseek','--question','q','--max-search-attempts','1'])
  with self.assertRaises(SystemExit):cli.parse_args(['--model','baidu_ai','--question','q','--max-search-attempts','0'])

if __name__=='__main__':unittest.main()

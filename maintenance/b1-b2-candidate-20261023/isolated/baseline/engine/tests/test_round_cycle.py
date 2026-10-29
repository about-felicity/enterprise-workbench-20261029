from pathlib import Path
import tempfile
import unittest
from geo_source_cards.journal import Journal
class Tests(unittest.TestCase):
    def test_cycles_questions_before_next_round_without_replacing_ids_or_completed_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);journal=Journal(root/'tasks.sqlite')
            try:
                rows=journal.plan('same','deepseek',['甲问题','乙问题'],2,root/'out.jsonl')
                self.assertEqual([(r['question'],r['round']) for r in rows],[('甲问题',1),('乙问题',1),('甲问题',2),('乙问题',2)])
                ids=[r['task_id'] for r in rows]
                journal.start(ids[0]);journal.complete(ids[0],{'answer':'done'})
                again=journal.plan('same','deepseek',['甲问题','乙问题'],2,root/'out.jsonl')
                self.assertEqual([r['task_id'] for r in again],ids)
                self.assertEqual(again[0]['state'],'completed')
            finally:journal.close()
if __name__=='__main__':unittest.main()

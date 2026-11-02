import json
import tempfile
import unittest
from pathlib import Path
from . import materials
from geo_source_cards.source_analysis import load_records


class JsonlRecordsTests(unittest.TestCase):
    def test_unicode_separators_preserved_and_duplicates_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            path=root/'days/2026-10-31/baidu_ai/results.jsonl'
            path.parent.mkdir(parents=True)
            row={'question':'题目','model':'baidu_ai','task_id':'a','captured_at':1,
                 'text':'原文\u0085下一段\u2028仍在原文\u2029末段','body_capture_complete':True}
            text=json.dumps(row,ensure_ascii=False)
            path.write_text(text+'\n'+text+'\n',encoding='utf8')
            self.assertEqual(materials.records('2026-10-31','题目',['baidu_ai'],root),[row])
            self.assertEqual(materials.read_lines(path),[row,row])
            self.assertEqual(load_records(path),[row,row])

    def test_real_corruption_is_not_silently_ignored(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'broken.jsonl'
            path.write_text('{"question":"truncated\n',encoding='utf8')
            for reader in (materials.read_lines,load_records):
                with self.assertRaises(json.JSONDecodeError):reader(path)

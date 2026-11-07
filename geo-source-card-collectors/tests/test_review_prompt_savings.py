import json
import tempfile
import unittest
from pathlib import Path
from geo_source_cards.rewrite_v2.structure_parser import serialize_review_data


class ReviewPromptSavingsTests(unittest.TestCase):
    def test_lossless_compaction_and_pinned_recovery(self):
        data = {'reference': '完整 原文\n保留空格', 'proposed_skeleton': {'tone': '自然', 'article_structure': ['甲', '乙']}}
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            compact = serialize_review_data(data, folder)
            self.assertEqual(json.loads(compact), data)
            self.assertLess(len(compact), len(json.dumps(data, ensure_ascii=False)))
            (folder / 'api_state.json').write_text('{}')
            self.assertEqual(serialize_review_data(data, folder), compact)

    def test_existing_unmarked_request_keeps_exact_legacy_format(self):
        for name in ('api_state.json', 'request.json', 'response.json'):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as root:
                folder = Path(root)
                (folder / name).write_text('{}')
                data = {'reference': '原文', 'proposed_skeleton': {'tone': '自然'}}
                self.assertEqual(serialize_review_data(data, folder), json.dumps(data, ensure_ascii=False))
                self.assertFalse((folder / 'review_prompt_format.json').exists())

    def test_unknown_format_is_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root)
            (folder / 'review_prompt_format.json').write_text('{"protocol":"unknown"}')
            with self.assertRaises(ValueError):
                serialize_review_data({}, folder)

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from geo_source_cards.desktop_backend import review_article


class ReviewTests(unittest.TestCase):
    def test_version_bound_record_and_required_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / 'articles/2026-10-09/category/01'
            folder.mkdir(parents=True)
            (folder / 'article.docx').write_bytes(b'original')
            digest = hashlib.sha256(b'original').hexdigest()
            (folder / 'receipt.json').write_text(json.dumps({'word_sha256': digest, 'date': '2026-10-09', 'category': 'category', 'number': 1}))
            with self.assertRaises(ValueError):
                review_article(root, folder, 'rejected', '')
            record = review_article(root, folder, 'approved')
            self.assertEqual(record['word_sha256'], digest)
            self.assertTrue((root / 'user_reviews' / (digest + '.json')).exists())
            (folder / 'article.docx').write_bytes(b'changed')
            with self.assertRaises(ValueError):
                review_article(root, folder, 'approved')
            with self.assertRaises(ValueError):
                review_article(root, root.parent, 'approved')

import tempfile
import unittest
from pathlib import Path
from docx import Document
from geo_source_cards.word_export import export_docx


class WordLayoutTests(unittest.TestCase):
    def test_preserves_punctuation_lists_and_hierarchy(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'article.docx'
            export_docx('# 选购指南：怎么选？\n\n正文第一段。\n正文第二段。\n\n## 一、预算与规格\n\n### 包装细节\n\n1. 第一项\n2. **第二项**\n- 补充项', path)
            document = Document(path)
            paragraphs = document.paragraphs
            self.assertEqual(paragraphs[0].text, '选购指南：怎么选？')
            self.assertEqual(paragraphs[0].style.name, 'Title')
            self.assertEqual(paragraphs[3].text, '一、预算与规格')
            self.assertEqual(paragraphs[4].style.name, 'Heading 2')
            self.assertEqual([p.text for p in paragraphs[5:]], ['1. 第一项', '2. 第二项', '• 补充项'])
            self.assertGreater(document.styles['Title'].font.size.pt, document.styles['Normal'].font.size.pt)
            self.assertEqual(document.styles['Normal'].font.size.pt, 11)
            self.assertEqual(document.styles['Normal'].paragraph_format.first_line_indent.pt, 22)
            self.assertTrue(any(r.bold for r in paragraphs[6].runs))

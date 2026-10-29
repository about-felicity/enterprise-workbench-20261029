import json
import tempfile
import unittest
from pathlib import Path

from geo_source_cards.article_provenance import build, overview_html, original_html


class ProvenanceTests(unittest.TestCase):
    def test_uses_claim_and_outline_sources_with_original_text(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            writer = root / "writer"
            research = root / "research"
            writer.mkdir()
            research.mkdir()
            def put(path, value):
                path.write_text(json.dumps(value), encoding="utf8")
            put(research / "research_input.json", {"observations": [{"sources": [
                {"url": url, "article": {"status": "fetched", "text": "原文" + url}}
                for url in ["https://used", "https://outline", "https://unused"]]}]})
            put(research / "research_result.json", {"knowledge_units": [
                {"id": "KU1", "content": "摘录", "evidence": [{"url": "https://used", "quote": "原文"}]},
                {"id": "KU2", "evidence": [{"url": "https://outline", "quote": "原文"}]}]})
            put(writer / "claim_map.json", {"claims": [{"text": "正文", "evidence_ids": ["KU1", "PF1"]}]})
            put(writer / "knowledge_to_sections.json", {"sections": [{"id": "S1", "knowledge_ids": ["KU2"]}]})
            put(writer / "product.json", {"facts": [{"text": "规格", "approved": True}]})
            (writer / "draft.md").write_text("正文", encoding="utf8")
            packet = build(writer)
            self.assertEqual({"https://used", "https://outline"}, {x["url"] for x in packet["sources"]})
            self.assertEqual([], packet["missing_source_urls"])
            self.assertIn("规格", overview_html(packet))
            self.assertTrue(all(x["text"].startswith("原文") for x in packet["sources"]))

    def test_untrusted_source_markup_is_escaped(self):
        rendered = original_html({"title": "<script>x</script>", "text": "<img src=x>", "url": "javascript:x"})
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img", rendered)
        self.assertNotIn("href=", rendered)

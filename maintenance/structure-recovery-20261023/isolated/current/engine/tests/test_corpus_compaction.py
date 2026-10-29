import tempfile
import unittest
from pathlib import Path

from geo_source_cards.api_prompts import expand_references
from geo_source_cards.prompt_compaction import compact_input
from geo_source_cards.runtime import atomic_json


class CorpusCompactionTests(unittest.TestCase):
    def test_large_taxonomy_retains_every_source_with_bounded_excerpts(self):
        sources = [
            {
                "url": f"https://media.example/{i}",
                "article": {"text": ("选择容量与包装，核对购买条件。" * 200)},
            }
            for i in range(170)
        ]
        result = compact_input("taxonomy", {"articles": sources})
        self.assertEqual(len(result["articles"]), 170)
        self.assertTrue(all(s["article"]["text"] for s in result["articles"]))
        self.assertLess(
            sum(len(s["article"]["text"]) for s in result["articles"]), 28000
        )
        self.assertGreater(len(sources[0]["article"]["text"]), 1000)

    def test_research_selection_is_bounded_and_explicit(self):
        sources = [
            {
                "url": f"https://media.example/{i}",
                "article": {"text": "容量包装比较。" * 40 + str(i)},
            }
            for i in range(20)
        ]
        result = compact_input(
            "research",
            {
                "observations": [{"question": "如何选", "sources": sources}],
                "product": {},
            },
        )
        self.assertEqual(len(result["sources"]), 6)
        self.assertEqual(result["sampling"]["total_sources"], 20)
        self.assertEqual(len({s["url"] for s in result["sources"]}), 6)

    def test_taxonomy_ids_restore_urls_and_duplicate_references(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            atomic_json(
                root / "evidence_spans.json",
                {
                    "E1_1": {
                        "url": "https://media.example/1",
                        "quote": "第一篇原文证据连续文本",
                    },
                    "E2_1": {
                        "url": "https://media.example/2",
                        "quote": "第二篇原文证据连续文本",
                    },
                },
            )
            result = expand_references(
                "taxonomy",
                root,
                {
                    "categories": [
                        {
                            "sources": [
                                {"quote_id": "E1_1", "duplicate_of": ""},
                                {"quote_id": "E2_1", "duplicate_of": "E1_1"},
                            ]
                        }
                    ]
                },
            )
            self.assertEqual(
                result["categories"][0]["sources"][1]["duplicate_of"],
                "https://media.example/1",
            )
            self.assertEqual(
                result["categories"][0]["sources"][0]["url"], "https://media.example/1"
            )

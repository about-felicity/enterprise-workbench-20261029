import json
import tempfile
import unittest
from pathlib import Path

from geo_source_cards.api_prompts import expand_references
from geo_source_cards.deepseek_api import APIError
from geo_source_cards.runtime import atomic_json
from geo_source_cards.taxonomy_batches import classify


class FakeClient:
    def __init__(self, mode="valid"):
        self.mode, self.calls = mode, 0

    def complete(self, prompt, directory, **kwargs):
        self.calls += 1
        data = json.loads(prompt.rsplit("\n", 1)[-1])
        if "titles" in data:
            return {
                "categories": [
                    {
                        "id": "C1",
                        "label": "容量选购",
                        "description": "规格比较",
                        "writing_angles": ["按实际存货比较容量"],
                    }
                ]
            }
        rows = [
            {
                "source_id": s["source_id"],
                "category_id": "C1",
                "quote_id": s["spans"][0][0],
            }
            for s in data["sources"]
        ]
        if self.mode == "missing":
            rows.pop()
        if self.mode == "foreign":
            rows[0]["quote_id"] = "E999_1"
        if self.mode == "bad_category_once" and self.calls == 2:
            rows[-1]["category_id"] = "C12"
        return {"assignments": rows}


class TaxonomyBatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        atomic_json(
            self.root / "input.json",
            {
                "max_per_category": 1,
                "articles": [
                    {
                        "url": f"https://media.example/{i}",
                        "article": {
                            "title": f"容量比较{i}",
                            "text": f"第{i}篇比较容量包装和购买条件。" * 20,
                        },
                    }
                    for i in range(25)
                ],
            },
        )

    def test_all_sources_are_bound_to_exact_evidence_across_batches(self):
        client = FakeClient()
        result = expand_references(
            "taxonomy", self.root, classify(client, self.root, {"date": "2026-10-08"})
        )
        urls = [s["url"] for c in result["categories"] for s in c["sources"]]
        self.assertEqual(set(urls), {f"https://media.example/{i}" for i in range(25)})
        self.assertEqual(len(urls), 25)
        self.assertEqual(client.calls, 4)

    def test_omitted_source_blocks_completion(self):
        with self.assertRaisesRegex(APIError, "coverage_incomplete"):
            classify(FakeClient("missing"), self.root, {"date": "2026-10-08"})
        self.assertFalse((self.root / "call/response.json").exists())

    def test_bad_category_gets_one_separate_correction(self):
        client = FakeClient("bad_category_once")
        result = classify(client, self.root, {"date": "2026-10-09"})
        self.assertEqual(client.calls, 5)
        self.assertEqual(sum(len(c["sources"]) for c in result["categories"]), 25)
        self.assertTrue((self.root / "call/batch-000-validation.json").exists())

    def test_invented_evidence_id_blocks_completion(self):
        with self.assertRaisesRegex(APIError, "invalid_taxonomy_batch_assignment"):
            classify(FakeClient("foreign"), self.root, {"date": "2026-10-08"})
        self.assertFalse((self.root / "call/response.json").exists())

    def test_changed_input_is_not_replayed(self):
        classify(FakeClient(), self.root, {"date": "2026-10-08"})
        data = json.loads((self.root / "input.json").read_text(encoding="utf8"))
        data["max_per_category"] = 2
        atomic_json(self.root / "input.json", data)
        client = FakeClient()
        with self.assertRaisesRegex(APIError, "input_changed"):
            classify(client, self.root, {"date": "2026-10-08"})
        self.assertEqual(client.calls, 0)

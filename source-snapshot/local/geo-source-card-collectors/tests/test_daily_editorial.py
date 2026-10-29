import copy
import json
import tempfile
import unittest
from pathlib import Path

from geo_source_cards.daily_editorial import (
    media_identity,
    prepare_day,
    repair,
    safe_name,
    validate_taxonomy,
    withdraw,
)
from geo_source_cards.runtime import atomic_json


class DailyEditorialTests(unittest.TestCase):
    def test_research_roster_repair_preserves_sources_and_old_input(self):
        from geo_source_cards.source_contract import bind
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = 'd' * 24
            location = root / 'days/2026-10-10/jobs/排行类/01/research'
            sources = [{'url':'https://media.test/a', 'article':{'status':'fetched','title':'三款洗发水盘点',
                        'text':'甲洗发水\n列有侧柏叶、甘油和泛醇等成分。\n乙洗发水\n列有氨基酸、甘油和植物成分。\n丙洗发水\n列有薄荷提取物及清洁配方。'}}]
            blueprint = bind({'version':'two-genre-v1','genre':'ranking','primary_url':sources[0]['url'],
                              'products':[{'name':'选洗发水','excerpt':'选洗发水要看实际需求。'}]}, sources, '2026-10-10')
            original = {'observations':[{'sources':sources}], 'product':{'name':'产品','facts':[]}, 'reference_design':blueprint}
            atomic_json(location / 'research_input.json', original)
            path = root / 'queue' / identity
            atomic_json(path / 'ticket.json', {'id':identity,'stage':'research','state':'needs_attention',
                        'location':location.relative_to(root).as_posix(),
                        'meta':{'date':'2026-10-10','category':'排行类','number':1}})
            atomic_json(path / 'receipt.json', {'state':'failed'})
            result = repair(root, identity, '已经核对主参考原始标题，需要修复错误名单并保留当日原始证据。')
            ticket = json.loads((root / 'queue' / result['ticket'] / 'ticket.json').read_text('utf8'))
            corrected = json.loads((root / ticket['location'] / 'research_input.json').read_text('utf8'))
            self.assertEqual(corrected['observations'], original['observations'])
            self.assertEqual(corrected['reference_design']['source_contract'], blueprint['source_contract'])
            self.assertEqual([p['name'] for p in corrected['reference_design']['products']], ['甲洗发水','乙洗发水','丙洗发水'])
            self.assertEqual(json.loads((location / 'research_input.json').read_text('utf8')), original)
            self.assertEqual(json.loads((Path(result['archive']) / 'research/research_input.json').read_text('utf8')), original)
            with self.assertRaises(ValueError):
                repair(root, identity, '已经核对主参考原始标题，需要修复错误名单并保留当日原始证据。')

    def test_manual_repair_refuses_unknown_delivery_and_keeps_failed_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = "c" * 24
            writer = root / "days/2026-10-07/jobs/类别/01/writer"
            writer.mkdir(parents=True)
            for name in (
                "writing_prompt.md",
                "writing_job.json",
                "knowledge.json",
                "product.json",
                "writing_task.txt",
                "category.json",
                "batch_rules.md",
                "draft.md",
                "claim_map.json",
                "knowledge_to_sections.json",
            ):
                (writer / name).write_text("original rejected content", encoding="utf8")
            path = root / "queue" / identity
            atomic_json(
                path / "ticket.json",
                {
                    "id": identity,
                    "stage": "writer",
                    "location": writer.relative_to(root).as_posix(),
                    "state": "needs_attention",
                    "meta": {
                        "date": "2026-10-07",
                        "category": "类别",
                        "number": 1,
                        "revision": 3,
                    },
                },
            )
            reason = "人工核实后必须删除虚构亲测，保持正文与映射一致，重新完整交付。"
            with self.assertRaises(ValueError):
                repair(root, identity, reason)
            atomic_json(path / "receipt.json", {"status": "known delivered"})
            result = repair(root, identity, reason)
            self.assertEqual(
                (Path(result["archive"]) / "writer/draft.md").read_text(
                    encoding="utf8"
                ),
                "original rejected content",
            )
            self.assertEqual(
                json.loads(
                    (root / "queue" / result["ticket"] / "ticket.json").read_text()
                )["meta"]["manual_repair_round"],
                1,
            )
            with self.assertRaises(ValueError):
                repair(root, identity, reason)

    def test_manual_withdrawal_preserves_receipt_and_requires_new_revision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            identity = "a" * 24
            location = "days/2026-10-07/jobs/类别/01/review"
            writer = root / location
            writer = writer.parent / "writer"
            writer.mkdir(parents=True)
            for name in (
                "writing_prompt.md",
                "writing_job.json",
                "knowledge.json",
                "product.json",
                "writing_task.txt",
                "category.json",
                "batch_rules.md",
                "draft.md",
                "claim_map.json",
                "knowledge_to_sections.json",
            ):
                (writer / name).write_text("preserved input", encoding="utf8")
            approved = root / "approved/2026-10-07/类别/01"
            receipt = {
                "date": "2026-10-07",
                "category": "类别",
                "number": 1,
                "word_sha256": "d" * 64,
            }
            atomic_json(approved / "receipt.json", receipt)
            atomic_json(
                root / "queue" / identity / "ticket.json",
                {
                    "id": identity,
                    "stage": "review",
                    "state": "accepted",
                    "location": location,
                    "accepted_at": "2026-10-07T19:00:00+08:00",
                    "meta": receipt,
                },
            )
            result = withdraw(root, "2026-10-07", "类别", 1, "发现不支持的具体断言")
            self.assertFalse(approved.exists())
            archive = Path(result["archive"])
            self.assertEqual(
                json.loads((archive / "receipt.json").read_text(encoding="utf8")),
                receipt,
            )
            ticket = json.loads(
                (root / "queue" / result["ticket"] / "ticket.json").read_text(
                    encoding="utf8"
                )
            )
            self.assertEqual(ticket["state"], "pending")
            self.assertTrue(ticket["meta"]["manual_withdrawal"])
            self.assertIn(
                "发现不支持", (writer / "revision_note.txt").read_text(encoding="utf8")
            )
            with self.assertRaises(FileNotFoundError):
                withdraw(root, "2026-10-07", "类别", 1, "不能重复撤回")

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.sources = {
            f"https://media.test/{i}": {
                "article": {
                    "status": "fetched",
                    "text": f"来源{i}关于油性头皮选购的真实完整连续正文证据",
                }
            }
            for i in range(3)
        }
        self.taxonomy = {
            "categories": [
                {
                    "label": "油性头皮选购指南",
                    "description": "消费场景选购",
                    "writing_angles": ["按清洁需求对照"],
                    "sources": [
                        {"url": u, "quote": s["article"]["text"]}
                        for u, s in self.sources.items()
                    ],
                }
            ]
        }

    def test_domain_boundary_and_foreign_exclusion(self):
        registry = {"media.test": "国内媒体"}
        self.assertEqual(media_identity("https://m.media.test/a", registry), "国内媒体")
        self.assertIsNone(media_identity("https://media.test.foreign/a", registry))
        self.assertIsNone(
            media_identity("https://foreign.test/?url=media.test", registry)
        )

    def test_all_sources_must_have_real_category_evidence(self):
        validate_taxonomy(self.taxonomy, self.sources)
        invalid = copy.deepcopy(self.taxonomy)
        invalid["categories"][0]["sources"][0]["quote"] = "不存在于文章里的虚构证据原文"
        with self.assertRaises(ValueError):
            validate_taxonomy(invalid, self.sources)
        invalid = copy.deepcopy(self.taxonomy)
        invalid["categories"][0]["sources"].pop()
        with self.assertRaises(ValueError):
            validate_taxonomy(invalid, self.sources)

    def test_no_source_can_be_reassigned_to_make_extra_categories(self):
        invalid = copy.deepcopy(self.taxonomy)
        extra = copy.deepcopy(invalid["categories"][0])
        extra["label"] = "另一类"
        invalid["categories"].append(extra)
        with self.assertRaises(ValueError):
            validate_taxonomy(invalid, self.sources)

    def test_daily_prepare_filters_media_and_is_idempotent(self):
        input_path, product = self.root / "articles.jsonl", self.root / "product.json"
        rows = [
            {
                "question": "原始自然问题",
                "sources": [{"url": u, **s} for u, s in self.sources.items()]
                + [
                    {
                        "url": "https://foreign.test/p",
                        "article": {"status": "fetched", "text": "海外商品页面"},
                    }
                ],
            }
        ]
        input_path.write_text(
            json.dumps(rows[0], ensure_ascii=False) + "\n", encoding="utf8"
        )
        atomic_json(product, {"name": "产品", "facts": []})
        result = prepare_day(
            self.root / "server",
            input_path,
            product,
            "2026-10-07",
            registry={"media.test": "国内媒体"},
        )
        self.assertEqual(result["media_articles"], 3)
        self.assertEqual(
            result,
            prepare_day(
                self.root / "server",
                input_path,
                product,
                "2026-10-07",
                registry={"media.test": "国内媒体"},
            ),
        )
        self.assertEqual(
            len(list((self.root / "server/queue").glob("*/ticket.json"))), 1
        )
        atomic_json(product, {"name": "另一个产品", "facts": []})
        with self.assertRaisesRegex(ValueError, "Daily input changed"):
            prepare_day(
                self.root / "server",
                input_path,
                product,
                "2026-10-07",
                registry={"media.test": "国内媒体"},
            )
        with self.assertRaises(ValueError):
            prepare_day(
                self.root, input_path, product, "2026-10-08", max_per_category=101
            )

    def test_folder_names_cannot_traverse_outside_date(self):
        self.assertNotIn("/", safe_name("选购/分类"))
        with self.assertRaises(ValueError):
            safe_name("..")

    def test_no_media_means_no_writing_task(self):
        input_path, product = self.root / "a.jsonl", self.root / "p.json"
        input_path.write_text(
            json.dumps(
                {
                    "sources": [
                        {
                            "url": "https://foreign.test/a",
                            "article": {"status": "fetched", "text": "正文"},
                        }
                    ]
                }
            )
            + "\n"
        )
        atomic_json(product, {"name": "产品", "facts": []})
        result = prepare_day(self.root / "server", input_path, product, "2026-10-07")
        self.assertEqual(result["status"], "blocked_no_media_articles")
        self.assertFalse((self.root / "server/queue").exists())


if __name__ == "__main__":
    unittest.main()

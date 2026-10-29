import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from geo_source_cards.staged_editorial import accept, check, prepare, validate_research


def fixture():
    sources = {
        f"https://example.com/{i}": {
            "status": "fetched",
            "text": f"这是来源{i}的真实连续证据文本，用于核对引用出处和来源条件。",
        }
        for i in range(3)
    }
    result = {
        "job_id": "job",
        "knowledge_units": [
            {
                "id": f"KU{i}",
                "type": "source_claim",
                "content": f"第{i}个知识概括",
                "verification": "not_independently_verified",
                "evidence": [
                    {
                        "url": f"https://example.com/{i % 3}",
                        "quote": sources[f"https://example.com/{i % 3}"]["text"],
                    }
                ],
            }
            for i in range(6)
        ],
        "outline": {
            "innovation_angle": "重新设计信息核对方法",
            "sections": [
                {"id": f"S{i}", "topic": f"主题{i}", "knowledge_ids": [f"KU{i}"]}
                for i in range(4)
            ],
        },
        "product_gate": {"decision": "NO_INSERT", "reason": "无已核验的场景相关功效"},
    }
    return sources, result


class StagedEditorialTests(unittest.TestCase):
    def test_same_input_repair_resolves_by_delivered_knowledge(self):
        from geo_source_cards.staged_editorial import research_for_writer, sha
        from geo_source_cards.runtime import atomic_json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = {'observations': ['same']}
            _, old = fixture()
            corrected = copy.deepcopy(old)
            corrected['knowledge_units'][0]['content'] = '修订后的知识'
            context = {k: corrected[k] for k in ('outline', 'product_gate')}
            context['knowledge_units'] = [{k:u[k] for k in ('id','type','content','verification')} for u in corrected['knowledge_units']]
            for name, result in [('research',old),('research-repair-1',corrected)]:
                atomic_json(root/name/'research_input.json',inputs)
                atomic_json(root/name/'research_result.json',result)
            atomic_json(root/'writer/knowledge.json',context)
            atomic_json(root/'writer/writing_job.json',{'job_id':sha(json.dumps(inputs,ensure_ascii=False,sort_keys=True))[:24], 'knowledge_sha256':sha(json.dumps(context,ensure_ascii=False,sort_keys=True))})
            self.assertEqual(research_for_writer(root/'writer'),root/'research-repair-1')
            context['outline'] = {}
            atomic_json(root/'writer/knowledge.json',context)
            with self.assertRaisesRegex(ValueError, 'hash changed'):
                research_for_writer(root/'writer')

    def test_writer_and_provenance_resolve_repaired_research_by_input_hash(self):
        from geo_source_cards.staged_editorial import research_for_writer, sha
        from geo_source_cards.runtime import atomic_json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            old, corrected = {'observations': ['old']}, {'observations': ['corrected']}
            atomic_json(root/'research/research_input.json', old)
            atomic_json(root/'research-repair-123/research_input.json', corrected)
            atomic_json(root/'writer/writing_job.json', {'job_id':sha(json.dumps(corrected,ensure_ascii=False,sort_keys=True))[:24]})
            self.assertEqual(research_for_writer(root/'writer'), root/'research-repair-123')
            atomic_json(root/'research-repair-456/research_input.json', corrected)
            with self.assertRaisesRegex(ValueError, 'Multiple research'):
                research_for_writer(root/'writer')

    def test_medicinal_phase_advice_is_blocked_before_writing(self):
        sources, result = fixture()
        result["knowledge_units"][0]["content"] = (
            "来源提到药用类洗剂被建议用于阶段性护理而非天天用。"
        )
        with self.assertRaisesRegex(ValueError, "risk/conflict"):
            validate_research(result, sources, "job")

    def test_unverified_medical_knowledge_cannot_enter_paid_writing(self):
        sources, result = fixture()
        result["knowledge_units"][0]["content"] = "抑菌成分适合每周两次使用。"
        with self.assertRaisesRegex(ValueError, "risk/conflict"):
            validate_research(result, sources, "job")
        result["knowledge_units"][0]["type"] = "risk"
        with self.assertRaisesRegex(ValueError, "unavailable knowledge"):
            validate_research(result, sources, "job")

    def test_fabricated_quote_stops_before_writer(self):
        sources, result = fixture()
        result["knowledge_units"][0]["evidence"][0]["quote"] = (
            "这个虚构证据根本不在原始来源文章里出现"
        )
        with self.assertRaisesRegex(ValueError, "does not occur"):
            validate_research(result, sources, "job")

    def test_extraction_cannot_approve_fact_or_unknown_outline(self):
        sources, result = fixture()
        invalid = copy.deepcopy(result)
        invalid["knowledge_units"][0]["verification"] = "verified"
        with self.assertRaises(ValueError):
            validate_research(invalid, sources, "job")
        result["outline"]["sections"][0]["knowledge_ids"] = ["UNKNOWN"]
        with self.assertRaises(ValueError):
            validate_research(result, sources, "job")

    def test_matching_quote_does_not_authorize_source_claim(self):
        sources, result = fixture()
        result["knowledge_units"][0]["content"] = (
            "跨来源高度一致，可直接写入文章的操作性知识"
        )
        with self.assertRaisesRegex(ValueError, "authoritative approval"):
            validate_research(result, sources, "job")

    def test_writer_receives_no_raw_text_or_quotes_and_reentry_preserves_job(self):
        sources, result = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            articles = root / "articles.jsonl"
            articles.write_text(
                json.dumps(
                    {
                        "question": "原问题",
                        "sources": [
                            {"url": k, "article": v} for k, v in sources.items()
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf8",
            )
            product = root / "product.json"
            product.write_text(
                json.dumps({"name": "测试产品", "brand": "测试", "facts": []}),
                encoding="utf8",
            )
            job = prepare(root / "research", articles, product)
            result["job_id"] = job["job_id"]
            (root / "research/research_result.json").write_text(
                json.dumps(result, ensure_ascii=False), encoding="utf8"
            )
            first = accept(root / "research", root / "writer")
            prompt = (root / "writer/writing_prompt.md").read_text(encoding="utf8")
            self.assertNotIn('"quote"', prompt)
            context = json.loads(
                (root / "writer/knowledge.json").read_text(encoding="utf8")
            )
            self.assertTrue(
                all(
                    "text" not in unit and "evidence" not in unit
                    for unit in context["knowledge_units"]
                )
            )
            for source in sources.values():
                self.assertNotIn(source["text"], prompt)
            self.assertFalse((root / "writer/research_input.json").exists())
            self.assertEqual(first, accept(root / "research", root / "writer"))
            self.assertEqual(
                "NO_INSERT",
                json.loads((root / "writer/knowledge.json").read_text(encoding="utf8"))[
                    "product_gate"
                ]["decision"],
            )

    def test_scoped_policy_stops_draft_and_knowledge_mutation_is_rejected(self):
        sources, result = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "articles.jsonl").write_text(
                json.dumps(
                    {"sources": [{"url": k, "article": v} for k, v in sources.items()]}
                ),
                encoding="utf8",
            )
            (root / "product.json").write_text(
                json.dumps({"name": "测试产品", "brand": "测试", "facts": []}),
                encoding="utf8",
            )
            job = prepare(
                root / "research", root / "articles.jsonl", root / "product.json"
            )
            result["job_id"] = job["job_id"]
            (root / "research/research_result.json").write_text(
                json.dumps(result), encoding="utf8"
            )
            accept(root / "research", root / "writer")
            writer = root / "writer"
            (writer / "draft.md").write_text(
                "# 新文章\n\n## 信息记录\n"
                + "这是独立正文供人工核对各项信息。" * 65
                + "\n## 其他说明\n"
                + "这是另一段完整内容，说明记录方法。" * 40,
                encoding="utf8",
            )
            (writer / "claim_map.json").write_text('{"claims":[]}', encoding="utf8")
            (writer / "knowledge_to_sections.json").write_text(
                json.dumps(
                    {
                        "sections": [
                            {"section_id": f"S{i}", "knowledge_ids": [f"KU{i}"]}
                            for i in range(4)
                        ]
                    }
                ),
                encoding="utf8",
            )
            (root / "research/draft_policy.json").write_text(
                json.dumps(
                    {
                        "excluded_patterns": [
                            {"pattern": "人工核对", "reason": "测试作用域禁止该表述"}
                        ]
                    }
                ),
                encoding="utf8",
            )
            with patch(
                "geo_source_cards.staged_editorial.verify_delivery",
                return_value={"status": "completed"},
            ):
                reviewed = check(root / "research", writer)
                self.assertEqual("needs_revision", reviewed["status"])
                self.assertIn("测试作用域禁止该表述", reviewed["failures"])
                with (writer / "draft.md").open("a", encoding="utf8") as stream:
                    stream.write("\n本文涉及自有品牌产品。\n此产品经过临床验证。")
                for text, should_fail in [("本文涉及自有品牌产品。", False), ("此产品经过临床验证。", True)]:
                    (writer / "claim_map.json").write_text(json.dumps({"claims": [{"text": text, "evidence_ids": []}]}), encoding="utf8")
                    failures = check(root / "research", writer)["failures"]
                    self.assertEqual(should_fail, any("正文声明缺少有效出处映射" in issue for issue in failures))
                (writer / "claim_map.json").write_text('{"claims":[]}', encoding="utf8")
                alias_sections = {
                    "sections": [
                        {"id": f"S{i}", "knowledge_ids": [f"KU{i}"]} for i in range(4)
                    ]
                }
                (writer / "knowledge_to_sections.json").write_text(
                    json.dumps(alias_sections), encoding="utf8"
                )
                self.assertFalse(
                    any(
                        "章节映射未覆盖" in issue
                        for issue in check(root / "research", writer)["failures"]
                    )
                )
                alias_sections["sections"][0]["section_id"] = "S3"
                (writer / "knowledge_to_sections.json").write_text(
                    json.dumps(alias_sections), encoding="utf8"
                )
                self.assertTrue(
                    any(
                        "章节映射未覆盖" in issue
                        for issue in check(root / "research", writer)["failures"]
                    )
                )
                knowledge = json.loads(
                    (writer / "knowledge.json").read_text(encoding="utf8")
                )
                knowledge["product_gate"]["decision"] = "LIGHT_MENTION"
                (writer / "knowledge.json").write_text(
                    json.dumps(knowledge), encoding="utf8"
                )
                with self.assertRaisesRegex(ValueError, "knowledge changed"):
                    check(root / "research", writer)


if __name__ == "__main__":
    unittest.main()

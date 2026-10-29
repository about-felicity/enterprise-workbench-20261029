import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, Mock
from zipfile import ZipFile

import requests

from geo_source_cards.api_worker import Worker
from geo_source_cards.daily_editorial import publish_ticket, tick, prepare_day
from geo_source_cards.deepseek_api import DeepSeekClient, APIError
from geo_source_cards.runtime import atomic_json
from geo_source_cards.staged_editorial import read
from geo_source_cards.rewrite_v2 import integration, material_manager, quality_reviewer, structure_parser
from geo_source_cards.rewrite_v2.common import digest, seal, prompt_material

SKELETON = {"article_type": "ranking", "tone": "平实的资料比较，编辑视角",
    "article_structure": ["提出如何比较产品的问题", "先给出比较标准，再介绍第一款自有产品", "比较第二款的不同规格", "总结选择与局限"],
    "writing_rhythm": "问题→标准→产品→总结", "special_style_elements": [], "forbidden_pattern": []}
PRODUCT = {"name": "甲洗发水", "brand": "甲", "facts": [
    {"text": "规格200ml，品牌测试摘要：4周指标下降43.96%，存在个体差异。", "approved": True},
    {"text": "配方含植物提取物。报告编号TEST-123。价格158元。", "approved": True}],
    "raw_source_text": "规格200ml。4周指标下降43.96%。报告编号TEST-123。未提供样本量。"}
REFERENCE = "# 洗护产品如何选\n\n先考虑比较标准。\n\n第一款旧品牌洗发水200ml。\n\n第二款乙洗发水300ml。\n\n结合需求选择，注意个体差异。"
DRAFT = "# 两款洗发水怎么选择\n\n比较之前先了解规格和资料。本文涉及自有品牌产品。\n\n## 第一款 甲洗发水\n\n甲洗发水规格200ml。品牌摘要记录4周指标下降43.96%，存在个体差异，未提供样本量。\n\n## 第二款 乙洗发水\n\n参考资料记载乙洗发水300ml。\n\n## 选择与边界\n\n按自己的需求选择，这些品牌资料不代表每个人的使用结果。\n"


def verdict(passed=True):
    return {"pass": passed, "issue": "" if passed else "开头问题与结尾没有衔接",
            "revise_instruction": "" if passed else "统一全文主线并完整重写"}


class MaterialWhitespaceTests(unittest.TestCase):
    def test_source_once_projection_keeps_full_original_and_additional_facts(self):
        from geo_source_cards.rewrite_v2.common import evidence_product
        material = {'raw_product': {'name':'甲','raw_source_text':'规格5ml\n价格369元',
            'facts':[{'text':'规格5ml 价格369元','approved':True},{'text':'用户确认新版价格350元','approved':True}]},
            'layers':{},'usage_rules':[]}
        before = copy.deepcopy(material)
        value = evidence_product(material)
        self.assertEqual(value['raw_source_text'],material['raw_product']['raw_source_text'])
        self.assertEqual([f['text'] for f in value['facts']],['用户确认新版价格350元'])
        self.assertEqual(material,before)
    def test_writer_output_limit_preserves_sent_request_and_minimum_complete_draft(self):
        from geo_source_cards.rewrite_v2.full_writer import output_limit
        from geo_source_cards.deepseek_api import request_payload
        from geo_source_cards.api_budget import INPUT_MISS, OUTPUT
        prompt = '写完整文章';size = len(json.dumps(request_payload(prompt, 0)['messages'], ensure_ascii=False).encode('utf8'))+256
        client = Mock();client.budget.remaining.return_value = size*INPUT_MISS/1000000+8001*OUTPUT/1000000
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp);limit = output_limit(client,prompt,folder,{})
            self.assertEqual(limit,8000)
            atomic_json(folder/'api_state.json',{'state':'REQUESTING'});atomic_json(folder/'request.json',{'max_tokens':limit})
            client.budget.remaining.return_value = 0
            self.assertEqual(output_limit(client,prompt,folder,{}),limit)
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(output_limit(client,prompt,Path(tmp),{}),6000)

    def test_prompt_compaction_roundtrips_every_source_field_without_mutation(self):
        product = {'name': '产品', 'raw_source_text': '完整原始资料', 'facts': [
            {'text': '40%', 'evidence': '品牌Word', 'approved': True, 'report': {'method': 'A'}},
            {'text': '5ml', 'evidence': '品牌Word', 'approved': True, 'report': {'method': 'B'}}]}
        material = {'raw_product': product, 'layers': {'test_data': ['40%']}, 'usage_rules': ['保留归属']}
        before = copy.deepcopy(material);compact = prompt_material(material)
        self.assertEqual(material, before)
        restored = dict(compact['raw_product']);defaults = restored.pop('fact_defaults')
        restored['facts'] = [{**defaults, **f} for f in restored['facts']]
        self.assertEqual(restored, product)
        self.assertEqual(compact['layers'], material['layers'])
        self.assertEqual(compact['usage_rules'], material['usage_rules'])

    def test_table_rows_restore_exact_original_whitespace_without_new_call(self):
        product = {'name': '眉毛精华液', 'raw_source_text': 'pH值\n-\n检测方法\n4.0-8.5\n5.9\n合格'}
        value = {k: [] for k in material_manager.LAYERS}
        value['test_data'] = ['pH值 - 检测方法 4.0-8.5 5.9 合格']
        with tempfile.TemporaryDirectory() as tmp:
            result = material_manager.restore_quote_whitespace(value, product, Path(tmp))
            self.assertEqual(result['test_data'], [product['raw_source_text']])
            material_manager.validate(result, material_manager.raw_material(product))
            proof = read(Path(tmp) / 'quote_whitespace_projection.json')
            self.assertEqual(proof['additional_model_calls'], 0)
            self.assertEqual(value['test_data'][0], 'pH值 - 检测方法 4.0-8.5 5.9 合格')

    def test_table_projection_rejects_changed_number_unit_or_missing_condition(self):
        product = {'name': '眉毛精华液', 'raw_source_text': '检测值\n5.9 mg/kg\n4周\n合格'}
        for quote in ['检测值 6.0 mg/kg 4周 合格', '检测值 5.9 g/kg 4周 合格', '检测值 5.9 mg/kg 合格']:
            value = {k: [] for k in material_manager.LAYERS};value['test_data'] = [quote]
            with tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises(ValueError):material_manager.restore_quote_whitespace(value, product, Path(tmp))


class Response:
    status_code = 200
    def __init__(self, content):
        self.content = content
    def json(self):
        return {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(self.content, ensure_ascii=False)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 100}, "id": "fixture", "model": "fixture"}


class Session:
    """Only HTTP is substituted; actual client, disk protocol and queue run."""
    def __init__(self, *, styles=None, compliances=None):
        self.calls = []
        self.styles = list(styles or [True])
        self.compliances = list(compliances or [True])
        self.fail_stage = None
    def post(self, url, *, json, **kwargs):
        prompt = json["messages"][1]["content"]
        system = json['messages'][0]['content']
        if system.startswith('你是文章质量审核人'):
            self.calls.append(('evidence', json))
            reports = getattr(self, 'evidence_reports', [])
            return Response(reports.pop(0) if reports else {'findings': [], 'suggestions': ['可选：缩短导语']})
        if system.startswith('你是文章定点编辑'):
            self.calls.append(('repair', json))
            return Response(self.repair_answers.pop(0))
        kind = ("skeleton_review" if "你是独立语义骨架复核人" in prompt else
                "parser" if "你是文章语义解构专家" in prompt else
                "material" if "你是素材整理专家" in prompt else
                "style" if "你是独立风格及全文逻辑审稿人" in prompt else
                "compliance" if "你是独立事实与合规审稿人" in prompt else "writer")
        self.calls.append((kind, json))
        if self.fail_stage == kind:
            raise requests.Timeout("simulated uncertain delivery")
        if kind in {"parser", "skeleton_review"}: result = copy.deepcopy(SKELETON)
        elif kind == "material":
            result = {k: [] for k in material_manager.LAYERS}
            result["test_data"] = ["4周指标下降43.96%"]
            result["limitations"] = ["存在个体差异"]
        elif kind == "writer": result = {"draft_markdown": getattr(self, 'draft', DRAFT)}
        elif kind == "style": result = verdict(self.styles.pop(0) if len(self.styles) > 1 else self.styles[0])
        else: result = verdict(self.compliances.pop(0) if len(self.compliances) > 1 else self.compliances[0])
        return Response(result)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / "creation-123-abcdef01"
        self.root.mkdir()
        self.cache = self.base / "cache"
        self.day = "2026-10-23"
        atomic_json(self.root / "rewrite_policy.json", {"workflow": "rewrite-v2", "cache_dir": str(self.cache)})
        atomic_json(self.root / "job.json", {"job_id": self.root.name, "date": self.day, "task_name": "验证任务"})
        atomic_json(self.root / "logic_policy.json", {"required": True, "version": "rewrite-v2"})
        atomic_json(self.root / "days" / self.day / "day.json", {"date": self.day, "status": "producing", "planned_articles": 1})
        atomic_json(self.root / "days" / self.day / "product.json", PRODUCT)
        self.location = self.root / "days" / self.day / "jobs" / "排行类" / "01" / "research"
        self.observations = [{"question": "洗发水如何选", "sources": [{"url": "https://example.test/ref", "article": {
            "status": "fetched", "title": "洗护产品如何选", "text": REFERENCE}}]}]
        integration.prepare_research(self.location, self.observations, PRODUCT)
        atomic_json(self.location.parent / "category.json", {"label": "排行类", "number": 1, "source_urls": ["https://example.test/ref"]})
        self.meta = {"date": self.day, "category": "排行类", "number": 1}
        self.ticket = publish_ticket(self.root, "research", self.location,
            ["research_input.json", "research_task.txt"], ["research_result.json"], self.meta)
        self.key = self.base / "key"
        self.key.write_text("sk-" + "x" * 30)
        self.session = Session()
        self.client = DeepSeekClient(self.key, session=self.session)
        self.worker = Worker(self.root, self.client)

    def approve(self):
        value = read(next((self.cache / "skeleton").glob("*.json")))
        return structure_parser.approve(self.cache, value["cache_key"], value["sha256"], "test human")

    def advance(self, count=6):
        for _ in range(count): self.worker.once(self.day)

    def completed(self):
        return self.root / "approved" / self.day / "排行类" / "01"

    def test_direct_output_exports_without_review_or_material_model_calls(self):
        atomic_json(self.root / 'rewrite_policy.json', {'workflow':'rewrite-v2', 'cache_dir':str(self.cache),
            'article_delivery':'direct', 'skeleton_review':'automatic', 'authorization':'user requests direct output'})
        self.session.draft = DRAFT.removeprefix('# ')
        self.advance(8)
        receipt = read(self.completed() / 'receipt.json')
        self.assertEqual(receipt['delivery_mode'], 'direct')
        self.assertEqual(receipt['quality_status'], 'unreviewed')
        self.assertEqual((self.completed() / 'draft.md').read_text(), DRAFT)
        self.assertFalse({'material','style','compliance'} & {k for k,_ in self.session.calls})
        self.assertFalse(any(read(p)['stage']=='review' for p in (self.root/'queue').glob('*/ticket.json')))
        with ZipFile(self.completed() / 'article.docx') as z:self.assertIn('word/document.xml',z.namelist())

    def test_delegated_automatic_review_reaches_delivery_without_human_action(self):
        atomic_json(self.root / 'rewrite_policy.json', {'workflow': 'rewrite-v2',
            'cache_dir': str(self.cache), 'skeleton_review': 'automatic',
            'authorization': 'User requests unattended full workflow'})
        self.advance(8)
        receipt = read(self.completed() / 'receipt.json')
        self.assertEqual(receipt['status'], 'accepted_for_user_review')
        approval = read(self.completed() / 'rewrite_context.json')['skeleton']['approval']
        self.assertEqual(approval['kind'], 'automatic')
        self.assertFalse(approval['human_review_performed'])
        self.assertEqual([c[0] for c in self.session.calls],
            ['parser', 'skeleton_review', 'material', 'writer', 'style', 'compliance'])
        context = read(self.completed() / 'rewrite_context.json')
        count = len(self.session.calls)
        again = structure_parser.review_automatically(self.client, context['skeleton'], self.cache,
            self.base / 'repeat-review', self.meta, 'User requests unattended full workflow')
        self.assertEqual(again, context['skeleton'])
        self.assertEqual(len(self.session.calls), count)

    def test_automatic_review_requires_authorization_and_preserves_uncertain_gate(self):
        value = structure_parser.parse(self.client, REFERENCE, self.cache, self.base / 'parser', self.meta)
        with self.assertRaises(ValueError):
            structure_parser.review_automatically(self.client, value, self.cache, self.base / 'check', self.meta, '')
        self.session.fail_stage = 'skeleton_review'
        with self.assertRaises(APIError):
            structure_parser.review_automatically(self.client, value, self.cache, self.base / 'check', self.meta, 'User delegation')
        stored = read(self.cache / 'skeleton' / (value['cache_key'] + '.json'))
        self.assertIsNone(stored['approval'])

    def test_legacy_approved_skeleton_remains_readable_after_protocol_update(self):
        value = seal({'protocol': 'semantic-skeleton-v2.1',
            'cache_key': structure_parser.identity(REFERENCE, 'semantic-skeleton-v2.1'),
            'source_text': REFERENCE, 'skeleton': SKELETON,
            'approval': {'reviewer': 'previous human', 'skeleton_sha256': digest(SKELETON)}})
        self.assertEqual(structure_parser.checked(value, REFERENCE, approved=True), value)

    def test_human_gate_then_original_queue_to_word_and_existing_download(self):
        from creation import runtime
        self.advance(3)
        self.assertEqual([c[0] for c in self.session.calls], ["parser"])
        self.assertTrue(read(self.root / "queue" / self.ticket / "ticket.json")["waiting_skeleton"])
        self.assertFalse((self.location.parent / "writer").exists())
        self.approve()
        self.advance()
        self.assertEqual([c[0] for c in self.session.calls], ["parser", "material", "writer", "style", "compliance"])
        folder = self.completed()
        self.assertTrue((folder / "article.docx").exists())
        self.assertEqual(read(self.root / "days" / self.day / "day.json")["status"], "complete")
        items = runtime.articles(self.root)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["quality_status"], "ready")
        with patch.object(runtime, "BASE", self.base.parent), patch.object(runtime, "job_root", return_value=self.root):
            path = runtime.download(self.root.name, items[0]["id"], "word", {})
            self.assertEqual(path.read_bytes(), (folder / "article.docx").read_bytes())
        from creation.article_export import write_article
        with ZipFile(self.base / "test.zip", "w") as archive: write_article(archive, self.root, items[0])
        with ZipFile(self.base / "test.zip") as archive:
            self.assertIsNone(archive.testzip())
            self.assertTrue(any(n.endswith("rewrite_material.json") for n in archive.namelist()))
        self.assertFalse(read(folder / "receipt.json")["publication_approved"])

    def test_style_failure_skips_compliance_and_whole_rewrites_once(self):
        self.session.styles = [False, True]
        self.worker.once(self.day); self.approve(); self.advance(9)
        self.assertEqual([c[0] for c in self.session.calls], ["parser", "material", "writer", "style", "writer", "style", "compliance"])
        self.assertTrue((self.completed() / "receipt.json").exists())
        self.assertEqual(len(list((self.location.parent / "versions").glob("*/review.json"))), 1)
        writer_calls = [p for kind, p in self.session.calls if kind == "writer"]
        self.assertIn("唯一一次全文重写", writer_calls[1]["messages"][1]["content"])

    def test_compliance_failure_rechecks_style_after_rewrite(self):
        self.session.compliances = [False, True]
        self.worker.once(self.day); self.approve(); self.advance(9)
        self.assertEqual([c[0] for c in self.session.calls][-5:], ["style", "compliance", "writer", "style", "compliance"])
        self.assertTrue((self.completed() / "receipt.json").exists())

    def test_second_rejection_never_enters_legacy_repair_or_download(self):
        self.session.styles = [False]
        self.worker.once(self.day); self.approve(); self.advance(12)
        self.assertEqual(sum(k == "writer" for k, _ in self.session.calls), 2)
        self.assertFalse(self.completed().exists())
        tickets = [read(p) for p in (self.root / "queue").glob("*/ticket.json")]
        self.assertEqual(sum(t["state"] == "needs_attention" for t in tickets), 1)

    def test_unknown_nested_request_is_never_resent(self):
        self.worker.once(self.day); self.approve()
        self.session.fail_stage = "material"
        for _ in range(2):
            with self.assertRaises(APIError) as error: self.worker.once(self.day)
            self.assertTrue(error.exception.uncertain)
        self.assertEqual([c[0] for c in self.session.calls], ["parser", "material"])

    def test_unknown_compliance_preserves_completed_style(self):
        self.worker.once(self.day); self.approve(); self.worker.once(self.day)
        self.session.fail_stage = "compliance"
        for _ in range(2):
            with self.assertRaises(APIError): self.worker.once(self.day)
        self.assertEqual([c[0] for c in self.session.calls], ["parser", "material", "writer", "style", "compliance"])

    def test_crash_after_writer_http_response_reuses_material_and_writer(self):
        self.worker.once(self.day); self.approve()
        real = integration.full_writer.generate
        def after_response(*args, **kwargs):
            real(*args, **kwargs)
            raise RuntimeError("simulated process crash after response")
        with patch.object(integration.full_writer, "generate", side_effect=after_response):
            with self.assertRaises(RuntimeError): self.worker.once(self.day)
        self.advance()
        self.assertEqual([c[0] for c in self.session.calls], ["parser", "material", "writer", "style", "compliance"])
        self.assertTrue((self.completed() / "receipt.json").exists())

    def test_cache_content_identity_and_approval_binding(self):
        self.worker.once(self.day)
        value = read(next((self.cache / "skeleton").glob("*.json")))
        self.assertIsNone(value["approval"])
        with self.assertRaises(ValueError): structure_parser.checked(value, REFERENCE, approved=True)
        with self.assertRaises(ValueError): structure_parser.approve(self.cache, value["cache_key"], "stale", "human")
        approved = self.approve()
        self.assertEqual(structure_parser.parse(self.client, REFERENCE, self.cache, self.base / "again", self.meta), approved)
        self.assertEqual(len(self.session.calls), 1)
        structure_parser.parse(self.client, REFERENCE + "新增段落", self.cache, self.base / "changed", self.meta)
        self.assertEqual(len(self.session.calls), 2)
        approved["skeleton"]["tone"] = "修改后未经确认"
        with self.assertRaises(ValueError): structure_parser.checked(seal(approved), REFERENCE, approved=True)

    def test_full_raw_material_reaches_writer_and_compliance(self):
        self.worker.once(self.day); self.approve(); self.advance()
        for kind, payload in self.session.calls:
            if kind in {"writer", "compliance"}:
                prompt = payload["messages"][1]["content"]
                for token in ("43.96%", "TEST-123", "158元", "300ml", "未提供样本量"):
                    self.assertIn(token, prompt)
        material = read(self.completed() / "rewrite_material.json")
        self.assertEqual(material["raw_product"], PRODUCT)

    def test_reviews_invalidated_by_each_input_change(self):
        self.worker.once(self.day); self.approve(); self.advance()
        folder = self.completed()
        result, context, material = (read(folder / p) for p in ("semantic_review.json", "rewrite_context.json", "rewrite_material.json"))
        for field in ("product", "reference", "category"):
            changed = copy.deepcopy(context); changed[field]["changed"] = True
            with self.assertRaises(ValueError): quality_reviewer.verify_final(result, changed, material, DRAFT)
        with self.assertRaises(ValueError): quality_reviewer.verify_final(result, context, material, DRAFT + "修改")
        changed = copy.deepcopy(material); changed["layers"]["limitations"] = []
        with self.assertRaises(ValueError): quality_reviewer.verify_final(result, context, seal(changed), DRAFT)

    def test_budget_rejection_does_not_call_or_create_rewrite(self):
        self.worker.once(self.day); self.approve()
        with patch.object(self.client, "complete", side_effect=APIError("article_budget_exceeded")):
            self.worker.once(self.day)
        self.assertEqual(len(self.session.calls), 1)
        self.assertFalse(self.completed().exists())
        self.assertTrue(any(read(p).get("error_code") == "article_budget_exceeded" for p in (self.root / "queue").glob("*/receipt.json")))

    def test_existing_taxonomy_enters_v2_without_legacy_structure_compiler(self):
        # Run the ordinary daily classification + queue path, not direct V2 helpers.
        other = self.base / "daily"
        atomic_json(other / "rewrite_policy.json", {"workflow": "rewrite-v2", "cache_dir": str(self.cache)})
        atomic_json(other / "product.json", PRODUCT)
        source = self.observations[0]["sources"][0]
        source = {**source, "article": {**source["article"], "title": "洗发水十大排名榜单", "text": REFERENCE * 5}}
        articles = self.base / "sources.jsonl"
        articles.write_text(json.dumps({"question": "洗发水排名", "sources": [source]}, ensure_ascii=False) + "\n", encoding="utf8")
        prepare_day(other, articles, other / "product.json", self.day, max_per_category=1, registry={"example.test": "fixture"})
        with patch("geo_source_cards.reference_design.design", side_effect=AssertionError("legacy design used")):
            Worker(other, self.client).once(self.day)
        tickets = [read(p) for p in (other / "queue").glob("*/ticket.json")]
        self.assertTrue(any(t["stage"] == "research" and t["meta"].get("workflow") == "rewrite-v2" for t in tickets))

    def test_confirmation_api_is_explicit_idempotent_and_keeps_pause(self):
        from creation import runtime
        self.worker.once(self.day)
        with patch.object(runtime, 'BASE', self.base), patch.object(runtime, 'job_root', return_value=self.root):
            pending = runtime.action('skeleton_inspect', {'job_id': self.root.name}, 'a' * 32)
            value = pending[0]
            atomic_json(self.root / 'control.json', {'paused': True, 'revision': 7})
            payload = {'job_id': self.root.name, 'key': value['cache_key'], 'expected_sha256': value['sha256'], 'reviewer': 'fixture human'}
            first = runtime.action('skeleton_approve', payload, 'b' * 32)
            self.assertEqual(runtime.action('skeleton_approve', payload, 'b' * 32), first)
            self.assertTrue(read(self.root / 'control.json')['paused'])
            self.assertEqual(len(self.session.calls), 1)
            self.assertEqual(sum(read(p)['stage'] == 'writer' for p in (self.root / 'queue').glob('*/ticket.json')), 1)

    def test_real_http_download_uses_existing_route_and_binary_headers(self):
        from creation import runtime
        from creation.service import Handler
        from http.server import ThreadingHTTPServer
        from urllib.request import urlopen
        from urllib.parse import urlencode
        import threading
        import hashlib
        self.worker.once(self.day); self.approve(); self.advance()
        item = runtime.articles(self.root)[0]
        server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True); thread.start()
        try:
            query = urlencode({'job': self.root.name, 'article': item['id'], 'kind': 'word'})
            with patch.object(runtime, 'job_root', return_value=self.root):
                with urlopen('http://127.0.0.1:' + str(server.server_port) + '/api/download?' + query) as response:
                    body = response.read()
                    self.assertEqual(hashlib.sha256(body).hexdigest(), response.headers['X-Content-SHA256'])
                    self.assertEqual(int(response.headers['X-Download-Bytes']), len(body))
                    self.assertEqual(body, (self.completed() / 'article.docx').read_bytes())
        finally:
            server.shutdown(); server.server_close(); thread.join()

    def test_changed_material_cannot_reuse_cached_classification(self):
        first = material_manager.process(self.client, PRODUCT, self.cache, self.base / 'mat1', self.meta)
        changed = {**PRODUCT, 'raw_source_text': PRODUCT['raw_source_text'] + '新版价格199元'}
        second = material_manager.process(self.client, changed, self.cache, self.base / 'mat2', self.meta)
        self.assertNotEqual(first['cache_key'], second['cache_key'])
        self.assertEqual(len(self.session.calls), 2)

    def test_science_skeleton_is_used_without_ranked_section_generation(self):
        self.worker.once(self.day)
        original = read(next((self.cache / 'skeleton').glob('*.json')))
        revised = {**SKELETON, 'article_type': 'popular_science',
                   'article_structure': ['提出问题', '解释比较标准', '自然引入产品案例', '回到问题并总结'],
                   'forbidden_pattern': ['TOP排名']}
        structure_parser.approve(self.cache, original['cache_key'], original['sha256'], 'fixture human', skeleton=revised)
        self.advance()
        prompt = next(p['messages'][1]['content'] for kind, p in self.session.calls if kind == 'writer')
        self.assertIn('popular_science', prompt)
        self.assertEqual(sum(kind == 'writer' for kind, _ in self.session.calls), 1)

    def test_provider_format_marker_is_removed_without_changing_raw_or_resending(self):
        raw = {'type': 'json_object', **copy.deepcopy(SKELETON)}
        post = self.session.post
        def metadata_response(url, **kwargs):
            post(url, **kwargs)
            return Response(raw)
        with patch.object(self.session, 'post', side_effect=metadata_response):
            first = structure_parser.parse(self.client, REFERENCE, self.cache, self.base / 'parser', self.meta)
        self.assertEqual(first['skeleton'], SKELETON)
        self.assertEqual(read(self.base / 'parser/response.json'), raw)
        self.assertEqual(read(self.base / 'parser/format_projection.json')['new_paid_requests'], 0)
        self.assertEqual(structure_parser.parse(self.client, REFERENCE, self.cache, self.base / 'parser', self.meta), first)
        self.assertEqual(len(self.session.calls), 1)

    def test_legacy_manual_repair_cannot_bypass_v2_rewrite_limit(self):
        from geo_source_cards.daily_editorial import repair
        self.session.styles = [False]
        self.worker.once(self.day); self.approve(); self.advance(12)
        ticket = next(read(p) for p in (self.root / 'queue').glob('*/ticket.json') if read(p)['state'] == 'needs_attention')
        with self.assertRaisesRegex(ValueError, 'V2'):
            repair(self.root, ticket['id'], 'This legacy repair must never create a third V2 draft.')
        self.assertEqual(sum(k == 'writer' for k, _ in self.session.calls), 2)

    def test_legacy_quality_sidecar_rejects_v2_article_before_copy_or_request(self):
        from creation import quality_repair
        self.worker.once(self.day); self.approve(); self.advance()
        with self.assertRaisesRegex(ValueError, 'V2'):
            quality_repair.prepare({'root': str(self.root), 'id': self.day + '/排行类/01'}, self.base / 'side')
        self.assertFalse((self.base / 'side').exists())

    def test_evidence_review_suggestions_publish_without_rewrite(self):
        policy = read(self.root / 'rewrite_policy.json')
        atomic_json(self.root / 'rewrite_policy.json', {**policy, 'review_policy': 'evidence-v3', 'max_targeted_repairs': 2})
        self.worker.once(self.day); self.approve(); self.advance(12)
        self.assertTrue(self.completed().exists())
        result = read(self.completed() / 'semantic_review.json')
        self.assertEqual(result['review_protocol'], 'evidence-v3')
        self.assertTrue(result['pass'])
        self.assertTrue(result['style_check']['optional_suggestions'])
        self.assertEqual(sum(k == 'writer' for k, _ in self.session.calls), 1)
        self.assertEqual(sum(k == 'evidence' for k, _ in self.session.calls), 1)

    def test_evidence_review_repairs_exact_span_and_rechecks_new_hash(self):
        policy = read(self.root / 'rewrite_policy.json')
        atomic_json(self.root / 'rewrite_policy.json', {**policy, 'review_policy': 'evidence-v3', 'max_targeted_repairs': 2})
        self.session.draft = DRAFT.replace('甲洗发水规格200ml', '甲洗发水规格2000ml')
        self.session.evidence_reports = [{'findings': [{'kind': 'identity_error',
            'article_quote': '甲洗发水规格2000ml', 'source_quote': '规格200ml',
            'reason': '规格多了一个0', 'correction': '把2000ml改为200ml'}], 'suggestions': []}]
        self.session.repair_answers = [{'edits': [{'old': '甲洗发水规格2000ml', 'new': '甲洗发水规格200ml'}]}]
        self.worker.once(self.day); self.approve(); self.advance(16)
        self.assertEqual((self.completed() / 'draft.md').read_text('utf8'), DRAFT)
        self.assertEqual(sum(k == 'writer' for k, _ in self.session.calls), 1)
        self.assertEqual(sum(k == 'repair' for k, _ in self.session.calls), 1)
        self.assertEqual(sum(k == 'evidence' for k, _ in self.session.calls), 2)
        self.assertTrue(list(self.location.parent.glob('versions/*/review.json')))
        tickets = [read(p) for p in (self.root / 'queue').glob('*/ticket.json')]
        self.assertTrue(any(t['meta'].get('targeted_repair_round') == 1 for t in tickets))
        self.assertFalse(any(t['meta'].get('rewrite_round') for t in tickets))

    def test_evidence_review_has_bounded_targeted_repairs(self):
        policy = read(self.root / 'rewrite_policy.json')
        atomic_json(self.root / 'rewrite_policy.json', {**policy, 'review_policy': 'evidence-v3', 'max_targeted_repairs': 2})
        self.session.draft = DRAFT.replace('甲洗发水规格200ml', '甲洗发水规格2000ml')
        self.session.evidence_reports = [{'findings': [{'kind': 'identity_error',
            'article_quote': f'甲洗发水规格{size}ml', 'source_quote': '规格200ml',
            'reason': '规格不符', 'correction': '修正规格'}], 'suggestions': []} for size in [2000, 20000, 200000]]
        self.session.repair_answers = [{'edits': [{'old': f'甲洗发水规格{a}ml', 'new': f'甲洗发水规格{b}ml'}]} for a,b in [(2000,20000),(20000,200000)]]
        self.worker.once(self.day); self.approve(); self.advance(24)
        self.assertFalse(self.completed().exists())
        self.assertEqual(sum(k == 'repair' for k, _ in self.session.calls), 2)
        self.assertTrue(any(read(p).get('status') == 'TARGETED_REPAIR_LIMIT' for p in (self.root / 'queue').glob('*/auto_repair_blocked.json')))


class ProductSourceTests(unittest.TestCase):
    def test_old_product_snapshot_loads_its_own_original_word_only(self):
        from creation import studio
        with tempfile.TemporaryDirectory() as tmp, patch.object(studio, 'ROOT', Path(tmp)):
            product_id, upload, version = 'product-' + 'a' * 32, 'upload-' + 'b' * 32, 'c' * 64
            atomic_json(Path(tmp) / 'versions' / product_id / (version + '.json'), {
                'product': PRODUCT, 'word_source': {'import_id': upload, 'sha256': 'original'}})
            original_product = {k: v for k, v in PRODUCT.items() if k != 'raw_source_text'}
            atomic_json(Path(tmp) / 'versions' / product_id / (version + '.json'), {
                'product': original_product, 'word_source': {'import_id': upload, 'sha256': 'original'}})
            atomic_json(Path(tmp) / 'imports' / upload / 'extraction.json', {'sha256': 'original', 'text': '全量历史Word资料'})
            result = studio.complete_product_source(original_product, product_id, version)
            self.assertEqual(result['raw_source_text'], '全量历史Word资料')
            different = {**original_product, 'name': '另外一个产品'}
            self.assertEqual(studio.complete_product_source(different, product_id, version), different)
            self.assertNotIn('raw_source_text', original_product)


class SchemaTests(unittest.TestCase):
    def test_arithmetic_and_roster_checks_do_not_depend_on_model(self):
        context = {'product': {'name':'甲精华', 'raw_source_text':''}}
        draft = '# 10款精华\n\n## 甲精华\n\n**乙精华（8.5分）。** 15ml/199元，折算约0.13元/ml。\n'
        findings = quality_reviewer.deterministic_findings(context, draft)
        self.assertEqual({f['kind'] for f in findings}, {'broken_document', 'numeric_error'})
        corrected = draft.replace('10款','2款').replace('0.13','13.27')
        self.assertFalse(quality_reviewer.deterministic_findings(context, corrected))

    def test_unused_promotion_conflict_cannot_reject_correct_price_pairs(self):
        context = {'product':{'name':'甲','raw_source_text':'单支369/5ml；第二支半价573/10ml；买二送一788/15ml'}}
        f = {'kind':'numeric_error','article_quote':'一支装369元/5ml；两支装573元/10ml；三支装788元/15ml',
             'source_quote':'','reason':'原资料折扣矛盾','correction':'删去第二支半价'}
        result, dismissed = quality_reviewer.adjudicate({'findings':[f],'suggestions':[]},context,'# 文章\n')
        self.assertFalse(result['findings']);self.assertEqual(len(dismissed),1)
        for bad in [f['article_quote'].replace('573','553'), f['article_quote']+'，第二支半价']:
            result, dismissed = quality_reviewer.adjudicate({'findings':[{**f,'article_quote':bad}],'suggestions':[]},context,'# 文章\n')
            self.assertTrue(result['findings']);self.assertFalse(dismissed)

    def test_provably_invalid_objections_are_audited_not_repaired(self):
        source = '1000+真人实测，97%用户3个月后眉毛量增加40%，92%用户反馈眉毛韧性提升。三支装788/15ml。'
        context = {'product': {'name':'甲', 'raw_source_text':source}}
        quotes = [
            ('numeric_error','品牌公开资料称，1000+真人实测，97%用户3个月后眉毛量增加40%，92%用户反馈眉毛韧性提升。','要求更严的证据'),
            ('unsafe_instruction','使用中若出现发痒、发红等不适，应暂停使用并咨询专业人士。','改为继续适应'),
            ('numeric_error','三支装788元/15ml，按5ml一支计折合每支约263元','改为394元'),
            ('identity_error','京东、淘宝旗舰店','无需修改。')]
        findings = [{'kind':k,'article_quote':q,'source_quote':'','reason':'模型意见','correction':c} for k,q,c in quotes]
        result, ignored = quality_reviewer.adjudicate({'findings':findings,'suggestions':[]},context,'# 文章\n')
        self.assertEqual(len(ignored),4)
        self.assertFalse(result['findings'])
        bad = {**findings[0], 'article_quote':quotes[0][1].replace('40%','400%')}
        result, ignored = quality_reviewer.adjudicate({'findings':[bad],'suggestions':[]},context,'# 文章\n')
        self.assertEqual(result['findings'],[bad])
        self.assertFalse(ignored)
        noop = {'kind':'numeric_error','article_quote':'品牌公布的活动价为：一支装369元/5ml，两支装573元/10ml，三支装788元/15ml。',
                'source_quote':'','reason':'错误指控折扣文案','correction':'只列金额和容量，改为“一支装369元/5ml，两支装573元/10ml，三支装788元/15ml”。'}
        projected, ignored = quality_reviewer.adjudicate({'findings':[noop],'suggestions':[]},context,'# 文章\n')
        self.assertFalse(projected['findings'])
        self.assertEqual(len(ignored),1)

    def test_evidence_cannot_invent_quote_or_treat_preferences_as_errors(self):
        context = {'reference': {'text': REFERENCE}}
        material = {'raw_product': PRODUCT}
        finding = {'kind': 'identity_error', 'article_quote': '甲洗发水规格200ml', 'source_quote': '规格200ml',
                   'reason': 'fixture', 'correction': 'fixture'}
        for change in [{'article_quote': '不存在的正文'}, {'source_quote': '虚构证据'}, {'kind': 'style_preference'}]:
            with self.assertRaises(ValueError):
                quality_reviewer.validate_findings({'findings': [{**finding, **change}], 'suggestions': []}, context, material, DRAFT)

    def test_exact_span_repair_rejects_ambiguous_overlapping_or_whole_article_edits(self):
        from geo_source_cards.rewrite_v2.targeted_repair import apply_edits
        for edits in [[{'old': '不存在', 'new': '改'}], [{'old': '甲洗发水', 'new': '其他'}],
                      [{'old': DRAFT, 'new': '# 改\n'}],
                      [{'old': '甲洗发水规格200ml', 'new': '修正'}, {'old': '规格200ml', 'new': '修正'}]]:
            with self.assertRaises(ValueError): apply_edits(DRAFT, {'edits': edits})

    def test_system_policy_is_in_request_identity(self):
        from geo_source_cards.deepseek_api import request_payload
        first = request_payload('资料', 2000)
        second = request_payload('资料', 2000, '新审稿标准')
        self.assertNotEqual(digest(first), digest(second))
        self.assertEqual(second['messages'][0]['content'], '新审稿标准')

    def test_optional_review_suggestions_do_not_require_rewrite(self):
        result = {'pass': True, 'issue': '', 'revise_instruction': '', 'optional_suggestions': '可选：减少重复句式'}
        self.assertTrue(quality_reviewer.validate(result)['pass'])
        with self.assertRaises(ValueError):
            quality_reviewer.validate({**result, 'issue': '存在必须改正的事实错误'})

    def test_material_cannot_invent_quote(self):
        value = {k: [] for k in material_manager.LAYERS}; value["test_data"] = ["效果100%"]
        with self.assertRaises(ValueError): material_manager.validate(value, material_manager.raw_material(PRODUCT))

    def test_malformed_or_contradictory_reviews_fail_closed(self):
        for value in ({}, {"pass": "true", "issue": "", "revise_instruction": ""},
                      {"pass": False, "issue": "", "revise_instruction": ""},
                      {"pass": True, "issue": "", "revise_instruction": "必须重写"},
                      {"pass": True, "issue": "存在错误", "revise_instruction": ""}):
            with self.assertRaises(ValueError): quality_reviewer.validate(value)


if __name__ == "__main__": unittest.main()

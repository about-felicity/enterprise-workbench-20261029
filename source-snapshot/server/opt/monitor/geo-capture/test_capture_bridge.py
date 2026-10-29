import copy
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "geo-source-card-collectors"))
import capture_bridge as bridge
import completion_guard
from geo_source_cards import cli


def fixture(round_number=1):
    value = {"question": "测试问题", "body": "完整正文\n第二段[1]", "sources": [
        {"url": "https://example.com/one", "title": "完整标题", "media": "媒体"}],
        "body_capture_complete": True, "source_capture_complete": True, "expected_source_count": 1,
        "capture_mode": "baidu_search_ai", "captured_at": "2026-10-15T09:00:00+08:00",
        "source_entries": [{"index": 1, "url": "https://example.com/one"}],
        "round": round_number, "task_id": "task" + str(round_number), "batch": "test"}
    return {"task_id": value["task_id"], "batch": "test", "ordinal": 0, "round": round_number,
            "state": "completed", "finished": 1000 + round_number, "result": json.dumps(value)}, value


def receipt(item):
    return {"request_id": item["request_id"], "model": item["model"], "source_device": item["source_device"],
            "stored_run_id": "stored", "analysis": {"answer_present": True,
            "answer_length": len(item["record"]["web_body"]), "body_capture_complete": True,
            "source_capture_complete": True, "source_count": 1,
            "sources": [{"title": "完整标题", "href": "https://example.com/one"}]}}


class CaptureBridgeTests(unittest.TestCase):
    def setUp(self):
        self.config = {"model": "baidu_ai", "rounds": 5, "device": "geo-baidu"}

    def test_doubao_guard_skips_only_a_fully_processed_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'new-batch-health.json'
            self.assertFalse(completion_guard.is_complete(path))
            good = {'planned': 105, 'captured': 105, 'geo_processed': 105, 'status': 'complete'}
            bridge.atomic_json(path, good)
            self.assertTrue(completion_guard.is_complete(path))
            for change in ({'geo_processed': 104}, {'status': 'running'}, {'tasks': {'needs_attention': 1}}):
                bridge.atomic_json(path, {**good, **change})
                self.assertFalse(completion_guard.is_complete(path))

    def test_receiver_hash_contract_and_raw_fidelity(self):
        row, value = fixture()
        item = bridge.envelope(row, value, self.config)
        raw = json.dumps(item["record"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        self.assertEqual(item["request_id"], hashlib.sha256(("wenxin\ngeo-baidu\n" + raw).encode()).hexdigest())
        self.assertEqual(item["record"]["capture_result"], value)
        self.assertEqual(item["record"]["web_body"], value["body"])
        self.assertEqual(item["record"]["source_entries"], value["source_entries"])

    def test_soak_recorder_rejects_changed_body_or_missing_source(self):
        from soak_monitor import fidelity
        row,value=fixture()
        item=bridge.envelope(row,value,self.config)
        result=fidelity(item,item['record'])
        self.assertEqual(result['sources'],1)
        for field,bad in (('web_body','被截断的回答'),('sources',[]),('source_entries',[])):
            changed={**item['record'],field:bad}
            with self.assertRaises(ValueError):fidelity(item,changed)

    def test_incomplete_absent_and_partial_are_not_full_answers(self):
        row, value = fixture()
        for change in ({"body_capture_complete": False}, {"source_capture_complete": None}, {"sources": []},
                       {"sources": [{"url": "https://example.com", "title": ""}]}):
            with self.assertRaises(ValueError):
                bridge.envelope(row, {**value, **change}, self.config)
        self.assertFalse(bridge.full_result({**value, "availability": "no_card"}))

    def test_receipt_must_match_exact_sources_and_complete_body(self):
        row, value = fixture()
        item = bridge.envelope(row, value, self.config)
        good = receipt(item)
        bridge.verify_receipt(good, item)
        for field, bad in (("answer_length", 1), ("source_capture_complete", False), ("quarantined", True),
                           ("sources", [])):
            changed = copy.deepcopy(good)
            changed["analysis"][field] = bad
            with self.assertRaises(ValueError):
                bridge.verify_receipt(changed, item)

    def test_duplicate_key_is_per_question_and_full_content(self):
        _, first = fixture()
        _, second = fixture(2)
        self.assertEqual(bridge.duplicate_key(first), bridge.duplicate_key(second))
        for change in ({"question": "另一个问题"}, {"body": "不同回答"}, {"source_entries": []},
                       {"sources": [{"url": "https://example.com/two", "title": "另一信源"}]}):
            self.assertNotEqual(bridge.duplicate_key(first), bridge.duplicate_key({**second, **change}))

    def test_durable_outbox_restart_and_baidu_duplicates_reuse_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bridge.atomic_json(root / "runtime/lan_result_receiver.json", {"port": 8791, "token": "test-token"})
            lane = root / "lane"
            rows = [fixture(1)[0], fixture(2)[0]]
            delivery = bridge.Delivery(lane, self.config, root)
            delivery.session = Mock()
            delivery.session.get.return_value.json.return_value = {'status': 'queued'}
            delivery.session.post.return_value.json.return_value = {"ok": True, "request_id": bridge.envelope(rows[0], fixture(1)[1], self.config)["request_id"]}
            result = delivery.sync(rows)
            self.assertEqual(result["duplicates"], 1)
            self.assertEqual(result["processed"], 0)
            self.assertEqual(delivery.session.post.call_count, 1)
            item = bridge.load(next((lane / "outbox").glob("*.json")))
            bridge.atomic_json(root / "runtime/lan_result_receiver/wenxin/done" / (item["request_id"] + ".json"), receipt(item))
            restarted = bridge.Delivery(lane, self.config, root)
            restarted.session = Mock()
            restarted.session.get.return_value.json.return_value = {'status': 'processed', 'receipt': receipt(item)}
            result = restarted.sync(rows)
            self.assertEqual((result["unique"], result["processed"], result["unique_processed"]), (1, 2, 1))
            restarted.session.post.assert_not_called()
            self.assertEqual(len(list((lane / "receipts").glob("*.json"))), 1)

    def test_wenxin_and_deepseek_rounds_are_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bridge.atomic_json(root / "runtime/lan_result_receiver.json", {"port": 8791, "token": "test-token"})
            for model in ("wenxin_card", "deepseek"):
                delivery = bridge.Delivery(root / model, {**self.config, "model": model}, root)
                delivery.session = Mock()
                delivery.session.get.return_value.json.return_value = {'status': 'queued'}
                items = [bridge.envelope(fixture(n)[0], fixture(n)[1], {**self.config, "model": model}) for n in (1, 2)]
                delivery.session.post.side_effect = [Mock(json=lambda i=i: {"ok": True, "request_id": i["request_id"]}) for i in items]
                result = delivery.sync([fixture(1)[0], fixture(2)[0]])
                self.assertEqual((result["unique"], result["duplicates"]), (2, 0))

    def test_cli_yields_one_result_then_resumes_original_batch_without_resending(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            args = cli.parse_args(["--model", "wenxin_card", "--runtime-dir", str(root / "collector"),
                                   "--question", "测试问题", "--rounds", "2", "--batch", "original",
                                   "--max-new-captures", "1", "--min-search-interval", "0"])
            collector = Mock()
            collector.collect_wenxin_search.side_effect = lambda *a, **kw: {**fixture()[1], "capture_mode": "baidu_wenxin_search"}
            with patch.dict(os.environ), patch.object(cli, "create_collector", return_value=collector):
                self.assertEqual(cli.run(args), 0)
                with closing(sqlite3.connect(root / "collector/tasks.sqlite")) as db:
                    self.assertEqual(dict(db.execute("select state,count(*) from captures group by state")), {"completed": 1, "pending": 1})
                self.assertEqual(cli.run(args), 0)
                self.assertEqual(cli.run(args), 0)
            self.assertEqual(collector.collect_wenxin_search.call_count, 2)


if __name__ == "__main__":
    unittest.main()

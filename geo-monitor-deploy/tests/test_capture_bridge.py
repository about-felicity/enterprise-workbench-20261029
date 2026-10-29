
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[1]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
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

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "geo-source-card-collectors"))
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
    def test_apply_drain_can_finish_unknown_original_without_unpausing_new_sends(self):
        from geo_source_cards.journal import Journal
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);batch='readback-drain'
            config={'model':'deepseek','rounds':1,'device':'geo-deepseek','batch':batch,'questions':['测试问题']}
            config_path=base/'config.json';bridge.atomic_json(config_path,config)
            lane=base/'batches'/batch
            journal=Journal(lane/'collector/tasks.sqlite')
            task=journal.plan(batch,'deepseek',config['questions'],1,lane/'results.jsonl')[0]
            with journal.db:journal.db.execute("update captures set state='needs_attention'")
            bridge.atomic_json(lane/'pause.json',{'allow_original_readback':True})
            def recover(*args,**kwargs):
                with journal.db:journal.db.execute("update captures set state='completed',result=?",(json.dumps(fixture()[1]),))
                child=Mock();child.poll.return_value=0;child.returncode=0;child.pid=123;return child
            def sync(rows):
                count=sum(r['state']=='completed' for r in rows)
                return {'captured':count,'processed':count,'unique':count,'unique_processed':count,'duplicates':0,'unavailable':0,'errors':[]}
            delivery=Mock();delivery.sync.side_effect=sync
            try:
                with patch.object(bridge,'Delivery',return_value=delivery),patch.object(bridge.subprocess,'Popen',side_effect=recover) as start,patch.object(bridge.time,'sleep'):
                    self.assertEqual(bridge.run(config_path,base,base),0)
                start.assert_called_once()
                self.assertTrue((lane/'pause.json').exists())
                self.assertTrue(start.call_args.kwargs['env']['GEO_CAPTURE_PAUSE_FILE'].endswith('/pause.json'))
            finally:journal.close()

    def setUp(self):
        self.config = {"model": "baidu_ai", "rounds": 5, "device": "geo-baidu"}

    def test_body_only_card_is_preserved_but_never_a_full_result_or_negative(self):
        row,value=fixture()
        value.update(availability='body_only',sources=[],source_capture_complete=False,
                     source_exposure='not_publicly_exposed',source_exposure_evidence={'card_present':True})
        row['result']=json.dumps(value)
        self.assertFalse(bridge.full_result(value))
        with self.assertRaises(ValueError):bridge.envelope(row,value,self.config)
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            bridge.atomic_json(root/'runtime/lan_result_receiver.json',{'port':8791,'token':'test-token'})
            delivery=bridge.Delivery(root/'capture',self.config,root)
            with patch.object(delivery.session,'get',side_effect=AssertionError('No full-result upload')):
                result=delivery.sync([row])
            self.assertEqual(result['body_only_observations'],1)
            self.assertEqual(result['captured'],0)
            observation=bridge.load(root/'capture/observations'/('task1.json'))
            self.assertEqual(observation['body'],value['body'])
            self.assertFalse(observation['source_capture_complete'])

    def test_child_exit_uses_final_journal_not_transient_failed_snapshot(self):
        from geo_source_cards.journal import Journal
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            config={**self.config,'batch':'exit-race','rounds':1,'questions':['测试问题']}
            config_path=base/'config.json'
            bridge.atomic_json(config_path,config)
            bridge.atomic_json(base/'runtime/lan_result_receiver.json',{'port':8791,'token':'test-token'})
            lane=base/'batches/exit-race'
            journal=Journal(lane/'collector/tasks.sqlite')
            task=journal.plan('exit-race','baidu_ai',['测试问题'],1,lane/'results.jsonl')[0]
            def start_child(*args,**kwargs):
                # A real SQLite transition visible while Chrome is closing.
                with journal.db:
                    journal.db.execute("update captures set state='failed_deferred' where task_id=?",(task['task_id'],))
                def exited():
                    # CLI persists the unavailable observation before exiting.
                    with journal.db:
                        journal.db.execute("update captures set state='completed',result=?,finished=1 where task_id=?",
                            (json.dumps({'availability':'supplement_unavailable'}),task['task_id']))
                    return 0
                return Mock(pid=12345,poll=exited,returncode=0)
            try:
                with patch.object(bridge,'STOP',False),patch.object(bridge.subprocess,'Popen',side_effect=start_child),patch.object(bridge.time,'sleep'):
                    result=bridge.run(config_path,base,base)
                self.assertEqual(result,0)
                health=bridge.load(lane/'bridge_health.json')
                self.assertEqual(health['status'],'complete_with_unavailable')
                self.assertEqual(health['unavailable'],1)
                self.assertEqual(health['tasks'],{'completed':1})
                self.assertEqual(list((lane/'outbox').glob('*.json')),[])
            finally:
                journal.close()

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

    def test_duplicate_classification_is_scoped_to_beijing_day(self):
        _, first = fixture()
        _, second = fixture(2)
        second['captured_at'] = '2026-10-16T09:00:00+08:00'
        self.assertNotEqual(bridge.duplicate_key(first), bridge.duplicate_key(second))
        second['captured_at'] = '2026-10-15T01:00:00Z'
        self.assertEqual(bridge.duplicate_key(first), bridge.duplicate_key(second))

    def test_durable_outbox_restart_preserves_every_baidu_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bridge.atomic_json(root / "runtime/lan_result_receiver.json", {"port": 8791, "token": "test-token"})
            lane = root / "lane"
            rows = [fixture(1)[0], fixture(2)[0]]
            delivery = bridge.Delivery(lane, self.config, root)
            delivery.session = Mock()
            delivery.session.get.return_value.json.return_value = {'status': 'queued'}
            items = [bridge.envelope(rows[n-1], fixture(n)[1], self.config) for n in (1, 2)]
            delivery.session.post.side_effect = [Mock(json=lambda i=i: {'ok': True, 'request_id': i['request_id']}) for i in items]
            result = delivery.sync(rows)
            self.assertEqual(result["duplicates"], 1)
            self.assertEqual(result["processed"], 0)
            self.assertEqual(delivery.session.post.call_count, 2)
            item = bridge.load(next((lane / "outbox").glob("*.json")))
            bridge.atomic_json(root / "runtime/lan_result_receiver/wenxin/done" / (item["request_id"] + ".json"), receipt(item))
            restarted = bridge.Delivery(lane, self.config, root)
            # A restart must preserve the original receipt polling backoff.
            for state in restarted.gate.states.values():state['next_at']=0
            restarted.session = Mock()
            restarted.session.get.side_effect = [Mock(json=lambda i=i: {'status': 'processed', 'receipt': receipt(i)}) for i in items]
            result = restarted.sync(rows)
            self.assertEqual((result["unique"], result["processed"], result["unique_processed"]), (1, 2, 1))
            restarted.session.post.assert_not_called()
            self.assertEqual(len(list((lane / "receipts").glob("*.json"))), 2)

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

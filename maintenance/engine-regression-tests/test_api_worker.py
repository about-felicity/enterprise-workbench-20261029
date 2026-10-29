import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from geo_source_cards.api_worker import Worker
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.deepseek_api import APIError, DeepSeekClient
from geo_source_cards.runtime import atomic_json
from geo_source_cards.staged_editorial import read


class WorkerRecoveryTests(unittest.TestCase):
    def test_local_article_budget_rejection_has_failed_receipt_without_job_pause(self):
        with patch.object(self.worker.client,'complete',side_effect=APIError('article_budget_exceeded')):
            self.worker.once('2026-10-07')
        receipt=read(self.root/'queue'/self.ticket/'receipt.json')
        self.assertEqual(receipt['error_code'],'article_budget_exceeded')
        self.assertEqual(read(self.root/'api/active.json')['state'],'SUBMITTED')
        self.session.post.assert_not_called()
        self.assertFalse((self.root/'control.json').exists())
    def test_logic_budget_rejection_keeps_completed_fact_review_without_resending(self):
        run_id='a'*24;execution={'run_id':run_id,'generation':1}
        job={**read(self.root/'queue'/self.ticket/'ticket.json'),'stage':'review','state':'claimed','client':self.worker.identity,'execution':execution}
        atomic_json(self.root/'queue'/self.ticket/'ticket.json',job)
        active={'ticket':self.ticket,'run_id':run_id,'state':'RESPONDED','execution':execution}
        answer={'checks':{str(i):True for i in range(7)},'failures':[]}
        atomic_json(self.root/'api/runs'/run_id/'answer.json',answer)
        self.worker.client.review_logic=Mock(side_effect=APIError('article_budget_exceeded'))
        self.worker.finish(job,active)
        self.assertEqual(read(self.root/'api/runs'/run_id/'answer.json'),answer)
        self.assertEqual(read(self.root/'queue'/self.ticket/'receipt.json')['error_code'],'article_budget_exceeded')
        self.session.post.assert_not_called()
        self.assertFalse((self.root/'control.json').exists())

    def test_article_material_preflight_rejection_does_not_send_or_pause_whole_job(self):
        location=self.root/'days/2026-10-07/jobs/排行类/01/writer'
        atomic_json(location.parent/'research/research_result.json',{'knowledge_units':[]})
        atomic_json(location.parent/'research/research_input.json',{'observations':[]})
        atomic_json(location.parent/'research/stage_job.json',{'job_id':'r'})
        atomic_json(location/'knowledge.json',{});atomic_json(location/'product.json',{})
        tid=publish_ticket(self.root,'writer',location,['knowledge.json','product.json'],['draft.md'],{'date':'2026-10-07','category':'排行类','number':1})
        original=read(self.root/'queue'/tid/'ticket.json');original['execution']={'run_id':'preflight','generation':1}
        active={'ticket':tid,'run_id':'preflight','state':'AUTHORIZING'}
        with patch('geo_source_cards.api_worker.authorize',return_value=original),patch('geo_source_cards.staged_editorial.validate_research'),patch('geo_source_cards.consumer_prompts.require_writer_material',side_effect=ValueError('主参考缺少产品中性资料')):
            result=self.worker.execute(original,active)
        self.assertEqual(result['stage'],'writer')
        self.session.post.assert_not_called()
        self.assertFalse((self.root/'control.json').exists())
        self.assertEqual(read(self.root/'api/active.json')['state'],'SUBMITTED')
        self.assertFalse(read(self.root/'api/runs/preflight/preflight_rejection.json')['request_sent'])
        self.assertEqual(read(self.root/'queue'/tid/'receipt.json')['error_code'],'research_material_insufficient')

    def test_cached_research_materializes_without_original_evidence_file(self):
        from geo_source_cards.api_worker import materialize
        from geo_source_cards.api_prompts import build_prompt

        atomic_json(
            self.location / "research_input.json",
            {
                "observations": [
                    {
                        "question": "容量怎么选",
                        "sources": [
                            {
                                "url": "https://example.org/a",
                                "article": {
                                    "title": "容量比较",
                                    "text": "这篇来源比较容量规格、包装形式与购买条件。"
                                    * 10,
                                },
                            }
                        ],
                    }
                ],
                "product": {"name": "示例"},
            },
        )
        job = {"stage": "research"}
        build_prompt(job, self.location)
        original = read(self.location / "evidence_spans.json")
        (self.location / "evidence_spans.json").unlink()
        materialize(
            job,
            self.location,
            {
                "units": [
                    {
                        "id": "KU01",
                        "kind": "opinion",
                        "text": "比较规格",
                        "evidence": [next(iter(original))],
                    }
                ],
                "angle": "比较容量",
                "sections": [],
                "gate": {"decision": "NO_INSERT"},
            },
        )
        self.assertEqual(read(self.location / "evidence_spans.json"), original)
        self.assertEqual(
            read(self.location / "research_result.json")["knowledge_units"][0][
                "evidence"
            ][0]["url"],
            "https://example.org/a",
        )
        self.session.post.assert_not_called()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.location = self.root / "days/2026-10-07/taxonomy"
        self.location.mkdir(parents=True)
        (self.location / "task.md").write_text(
            "Return JSON categories", encoding="utf8"
        )
        atomic_json(self.location / "input.json", {"articles": []})
        self.ticket = publish_ticket(
            self.root,
            "taxonomy",
            self.location,
            ["task.md", "input.json"],
            ["result.json"],
            {"date": "2026-10-07"},
        )
        key = self.root / "key"
        key.write_text("sk-" + "s" * 32, encoding="utf8")
        self.session = Mock()
        self.session.post.return_value.status_code = 200
        self.session.post.return_value.json.return_value = {
            "choices": [
                {"finish_reason": "stop", "message": {"content": '{"categories":[]}'}}
            ]
        }
        self.worker = Worker(self.root, DeepSeekClient(key, session=self.session))
        self.tick = patch("geo_source_cards.api_worker.tick")
        self.tick.start()
        self.addCleanup(self.tick.stop)

    def test_restart_before_authorization_resumes_without_lost_claim(self):
        self.worker.select("2026-10-07")
        self.assertEqual(read(self.root / "api/active.json")["state"], "AUTHORIZING")
        self.worker.once("2026-10-08")
        self.assertEqual(self.session.post.call_count, 1)
        self.assertEqual(read(self.root / "api/active.json")["state"], "SUBMITTED")

    def test_historical_failures_do_not_misreport_current_day(self):
        path = self.root/'queue'/self.ticket/'ticket.json'
        atomic_json(path,{**read(path),'state':'needs_attention'})
        result = self.worker.once('2026-10-08')
        self.assertEqual(result['status'],'idle')
        self.assertEqual(result['historical_failed_tickets'],1)
        self.assertEqual(result['failed_tickets'],0)
        result = self.worker.once('2026-10-07')
        self.assertEqual(result['status'],'needs_attention')
        self.assertEqual(result['failed_tickets'],1)
        self.session.post.assert_not_called()

    def test_two_genre_taxonomy_does_not_call_paid_api(self):
        from geo_source_cards.daily_editorial import file_hash
        path = self.location/'input.json'
        atomic_json(path, {'classification_version':'two-genre-v1','max_per_category':10,'articles':[{'url':'https://example.org/science','article':{'title':'清洁习惯的认识','text':'知识讲解文章介绍日常清洁习惯，说明常见问题与观察方法。'}}]})
        ticket_path = self.root/'queue'/self.ticket/'ticket.json'
        ticket = read(ticket_path)
        ticket['inputs']['input.json'] = file_hash(path)
        atomic_json(ticket_path,ticket)
        self.worker.once('2026-10-07')
        self.session.post.assert_not_called()
        delivery = self.root / 'queue' / self.ticket / 'delivery' / 'result.json'
        self.assertEqual('SUBMITTED', read(self.root / 'api/active.json')['state'])
        self.assertEqual('科普类', read(delivery)['categories'][0]['label'])

    def test_review_finishes_before_spending_on_more_research(self):
        old = read(self.root / "queue" / self.ticket / "ticket.json")
        atomic_json(
            self.root / "queue" / self.ticket / "ticket.json",
            {**old, "state": "accepted"},
        )
        publish_ticket(
            self.root,
            "research",
            self.location,
            ["task.md"],
            ["research_result.json"],
            {"date": "2026-10-07", "number": 2},
        )
        review = publish_ticket(
            self.root,
            "review",
            self.location,
            ["task.md"],
            ["result.json"],
            {"date": "2026-10-07", "number": 1},
        )
        self.assertEqual(self.worker.select("2026-10-07")["id"], review)

    def test_target_article_does_not_claim_unrelated_tasks(self):
        self.worker.target_article = ("2026-10-07", "指定类别", 1)
        self.assertIsNone(self.worker.select("2026-10-07"))
        self.assertEqual(
            read(self.root / "queue" / self.ticket / "ticket.json")["state"], "pending"
        )

    def test_restart_after_response_does_not_send_twice(self):
        with (
            patch.object(
                self.worker, "finish", side_effect=OSError("simulated process crash")
            ),
            self.assertRaises(OSError),
        ):
            self.worker.once("2026-10-07")
        active_path = self.root / "api/active.json"
        active = read(active_path)
        active["state"] = "REQUESTING"
        atomic_json(active_path, active)
        self.worker.once("2026-10-07")
        self.assertEqual(self.session.post.call_count, 1)
        self.assertTrue((self.root / "queue" / self.ticket / "receipt.json").is_file())

    def test_target_does_not_resume_another_articles_active_request(self):
        with (
            patch.object(self.worker, "finish", side_effect=OSError("crash")),
            self.assertRaises(OSError),
        ):
            self.worker.once("2026-10-07")
        before = (self.root / "api/active.json").read_bytes()
        self.worker.target_article = ("2026-10-07", "其他类别", 99)
        result = self.worker.once("2026-10-07")
        self.assertEqual(result["status"], "blocked_other_article_execution")
        self.assertEqual((self.root / "api/active.json").read_bytes(), before)
        self.assertEqual(self.session.post.call_count, 1)

    def test_receipt_window_recovery_preserves_existing_output(self):
        self.worker.once("2026-10-07")
        active_path = self.root / "api/active.json"
        active = read(active_path)
        receipt = self.root / "queue" / self.ticket / "receipt.json"
        previous = receipt.read_bytes()
        active["state"] = "RESPONDED"
        atomic_json(active_path, active)
        self.worker.once("2026-10-07")
        self.assertEqual(receipt.read_bytes(), previous)
        self.assertEqual(self.session.post.call_count, 1)

    def test_known_truncation_stops_without_automatic_paid_revision(self):
        self.session.post.return_value.json.return_value["choices"][0][
            "finish_reason"
        ] = "length"
        with self.assertRaisesRegex(APIError, "output_incomplete"):
            self.worker.once("2026-10-07")
        self.assertFalse((self.root / "queue" / self.ticket / "receipt.json").exists())
        # Restarting the worker cannot convert a known truncated response
        # into an automatic paid retry.
        restarted = Worker(self.root, self.worker.client)
        with self.assertRaisesRegex(APIError, "output_incomplete"):
            restarted.once("2026-10-07")
        self.assertEqual(self.session.post.call_count, 1)

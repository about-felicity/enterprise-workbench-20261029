import tempfile
import unittest
from pathlib import Path

from geo_source_cards.auto_repair import schedule, correction
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.runtime import atomic_json, atomic_write
from geo_source_cards.staged_editorial import read


class AutoRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.writer = self.root/'days/2026-10-13/jobs/science/01/writer'
        names = ['writing_prompt.md','writing_job.json','knowledge.json','product.json','writing_task.txt','category.json','batch_rules.md']
        for name in names:
            atomic_write(self.writer/name,'{}')
        self.identity = publish_ticket(self.root,'writer',self.writer,names,['draft.md'],{'date':'2026-10-13','category':'science','number':1,'revision':1})
        self.path = self.root/'queue'/self.identity/'ticket.json'
        self.job = {**read(self.path),'state':'needs_attention','error':'Draft checks rejected: 正文汉字不足：800'}
        atomic_json(self.path,self.job)
        atomic_json(self.path.parent/'receipt.json',{'state':'failed'})

    def test_recovery_is_durable_and_idempotent(self):
        self.assertEqual(schedule(self.root,'2026-10-13'),1)
        old=read(self.path)
        self.assertEqual(old['state'],'revision_requested')
        new=read(self.root/'queue'/old['replaced_by']/'ticket.json')
        self.assertEqual(new['meta']['auto_repair_round'],1)
        self.assertEqual(new['meta']['revision'],1)
        self.assertIn('不能摘要替代',(self.writer/'revision_note.txt').read_text('utf8'))
        self.assertEqual(schedule(self.root,'2026-10-13'),0)
        self.assertTrue((self.root/'repair_evidence'/('auto-'+self.identity)/'ticket/ticket.json').is_file())

    def test_ambiguous_delivery_is_never_retried(self):
        (self.path.parent/'receipt.json').unlink()
        self.assertEqual(schedule(self.root,'2026-10-13'),0)
        self.assertIsNone(correction('unknown_execution','writer'))
    def test_known_logic_rejection_gets_bounded_rewrite_and_keeps_reaudit(self):
        atomic_json(self.path,{**self.job,'stage':'review','error':'Logical review requests revision: actual contradictory conclusion'})
        self.assertEqual(schedule(self.root,'2026-10-13'),1)
        replacement=read(self.root/'queue'/read(self.path)['replaced_by']/'ticket.json')
        self.assertEqual(replacement['stage'],'writer')
        self.assertEqual(replacement['meta']['auto_repair_strategy'],'logic')
        self.assertIn('重新接受事实及全文逻辑审稿',(self.writer/'revision_note.txt').read_text('utf8'))

    def test_ranking_lead_failure_has_targeted_repair(self):
        strategy, note = correction('产品名单前至少500汉字的问题导入与选购依据', 'writer')
        self.assertEqual(strategy, 'introduction')
        self.assertIn('600—850', note)

    def test_old_day_and_pause_do_not_schedule(self):
        self.assertEqual(schedule(self.root,'2026-10-14'),0)
        atomic_json(self.root/'control.json',{'paused':True})
        self.assertEqual(schedule(self.root,'2026-10-13'),0)

    def test_limit_survives_restart(self):
        atomic_json(self.path,{**self.job,'meta':{**self.job['meta'],'auto_repair_round':3,'assisted_repair_round':2,'append_repair_round':1}})
        self.assertEqual(schedule(self.root,'2026-10-13'),0)
        self.assertEqual(schedule(self.root,'2026-10-13'),0)
        self.assertTrue((self.path.parent/'auto_repair_exhausted.json').is_file())

    def test_assisted_repair_preserves_exhausted_normal_count(self):
        atomic_json(self.path,{**self.job,'meta':{**self.job['meta'],'auto_repair_round':3}})
        self.assertEqual(schedule(self.root,'2026-10-13'),1)
        new=read(self.root/'queue'/read(self.path)['replaced_by']/'ticket.json')
        self.assertEqual(new['meta']['auto_repair_round'],3)
        self.assertEqual(new['meta']['assisted_repair_round'],1)
        self.assertEqual(schedule(self.root,'2026-10-13'),0)

    def test_inflight_article_is_not_repaired(self):
        active={**self.job,'id':'a'*24,'state':'claimed'}
        atomic_json(self.root/'queue'/active['id']/'ticket.json',active)
        self.assertEqual(schedule(self.root,'2026-10-13'),0)

    def test_a_local_response_replay_flag_is_not_inherited_by_new_paid_repairs(self):
        atomic_json(self.path,{**self.job,'meta':{**self.job['meta'],'known_response_replay':True}})
        self.assertEqual(schedule(self.root,'2026-10-13'),1)
        new=read(self.root/'queue'/read(self.path)['replaced_by']/'ticket.json')
        self.assertIs(new['meta']['known_response_replay'],False)

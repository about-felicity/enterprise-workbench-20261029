import json
import sqlite3
import threading
import unittest
from unittest.mock import patch
from monthly_monitoring import active_questions, overlay, owner, sync, target


def row(product='A', questions=None, active=True, month='2026-11-01'):
    return {'product': product, 'month': month, 'terms': [{'active': active,
            'versions': [{'questions': ['旧题'], 'windows': [[1, 2]]},
                         {'questions': questions or ['植萃染发剂推荐'], 'windows': [[2, None]]}]}]}


class MonthlyTests(unittest.TestCase):
    def test_current_active_latest_versions_and_shared_product_dedup(self):
        rows = [row(), row('B'), row('C', ['暂停题'], False), row('D', ['上月题'], month='2026-10-01')]
        self.assertEqual(active_questions(rows, '2026-11-09', 3), ['植萃染发剂推荐'])
        self.assertEqual(active_questions(rows, '2026-12-01', 3), [])
        self.assertEqual(active_questions(rows, '2026-11-09', 1), [])

    def test_shards_once_across_four_accounts_and_no_reshuffle(self):
        questions = ['二级词' + str(n) for n in range(42)]
        config = {'questions': ['推荐一款染发剂'], 'rounds': 5, 'interval': 60}
        assigned = []
        for model in ['doubao1', 'doubao2', 'doubao3', 'doubao4']:
            plan = overlay(config, model, questions, '2026-11-09')
            assigned.extend(plan['secondary_questions'])
            updated = overlay(plan, model, questions + ['新词'], '2026-11-09')
            self.assertEqual(plan['secondary_questions'], [q for q in updated['secondary_questions'] if q != '新词'])
        self.assertCountEqual(assigned, questions)

    def test_primary_targets_preserved_and_secondary_once(self):
        plan = overlay({'questions': ['大词'], 'rounds': 8, 'interval': 60}, 'wenxin_card', ['大词', '小词'], '2026-11-09')
        self.assertEqual([target(plan, q) for q in plan['questions']], [8, 1])
        updated = overlay(plan, 'wenxin_card', [], '2026-11-09')
        self.assertEqual(updated['questions'], ['大词'])

    def test_sync_idempotent_preserves_pause_and_batch(self):
        class Control:
            lock = threading.RLock()
            def connect(self): return self.db
        c = Control();c.db = sqlite3.connect(':memory:');c.db.row_factory = sqlite3.Row
        c.db.execute('create table daily_tasks(model,day,config,revision,desired,status,batch,updated,error)')
        c.db.execute('insert into daily_tasks values(?,?,?,?,?,?,?,?,?)', ('baidu_ai', '2026-11-09',
                     json.dumps({'questions': ['大词'], 'rounds': 5, 'interval': 60}), 1, 'paused', 'paused', 'current', 0, None))
        self.assertEqual(sync(c, '2026-11-09', [row()], 3)['changed'], ['baidu_ai'])
        self.assertEqual(sync(c, '2026-11-09', [row()], 4)['changed'], [])
        result = dict(c.db.execute('select * from daily_tasks').fetchone())
        self.assertEqual((result['revision'], result['desired'], result['batch']), (2, 'paused', 'current'))
        c.db.close()


class SchedulingTests(unittest.TestCase):
    def setUp(self):
        import test_control_panel as fixtures
        from daily_tasks import DailyTasks, today
        self.fixture = fixtures.ControlTests();self.fixture.setUp()
        self.c = self.fixture.control
        self.counts = {};self.c.daily_counts = lambda day: self.counts
        self.tasks = DailyTasks(self.c);self.day = today()

    def tearDown(self): self.fixture.tearDown()

    def configure(self, model='baidu_ai', rounds=5):
        with self.c.connect() as db:
            self.tasks.ensure_scheduled(db, model, self.day)
            cfg = overlay({'questions': ['大词'], 'rounds': rounds, 'interval': 60}, model, ['小词'], self.day)
            db.execute('update daily_tasks set config=? where model=? and day=?', (json.dumps(cfg), model, self.day))

    def test_no_start_or_pause_mid_answer_and_no_revision_churn(self):
        from control_panel import atomic
        self.configure()
        self.fixture.system.states['old-baidu_ai.service'] = 'active'
        with self.c.connect() as db: current = self.c.current(db, 'baidu_ai')
        rows = [row(month=self.day[:7]+'-01')]
        sync(self.c, self.day, rows, 3)
        self.tasks.reconcile()
        self.assertEqual(self.fixture.system.starts, [])
        self.assertFalse(self.c.marker(current).exists())

    def test_secondary_completes_once_without_five_round_repetition(self):
        from control_panel import atomic
        self.configure();self.counts['baidu_ai'] = {'大词': 5}
        self.tasks.reconcile()
        item = self.fixture.current('baidu_ai');cfg = item['current']['config']
        self.assertEqual((cfg['questions'], cfg['rounds']), (['小词'], 1))
        self.assertEqual(item['daily']['target'], 6)
        with self.c.connect() as db: job = self.c.current(db, 'baidu_ai')
        atomic(self.c.batch_root(job)/'bridge_health.json', {'status':'complete','captured':1,'processed':1,'geo_processed':1})
        self.fixture.system.states[job['service']] = 'inactive'
        self.counts['baidu_ai']['小词'] = 1
        self.tasks.reconcile()
        self.assertEqual(self.fixture.current('baidu_ai')['daily']['status'], 'complete')
        self.assertEqual(len(self.fixture.system.starts), 1)

    def test_wenxin_waits_for_baidu_secondary_too(self):
        self.configure();self.configure('wenxin_card', 8)
        self.counts['baidu_ai'] = {'大词': 5}
        self.tasks.reconcile()
        self.assertEqual(self.fixture.current('wenxin_card')['daily']['status'], 'waiting_for_baidu')

    def test_exhausted_baidu_slot_releases_wenxin_without_counting_as_sample(self):
        from pathlib import Path
        self.configure();self.configure('wenxin_card', 8)
        self.counts['baidu_ai'] = {'大词': 5}
        with self.c.connect() as db:
            job=self.c.current(db,'baidu_ai')
            config={**json.loads(job['config']),'daily_date':self.day}
            db.execute('update jobs set config=? where batch=?',(json.dumps(config),job['batch']))
        path=Path(job['health']).parent/'collector/tasks.sqlite'
        path.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect(path) as db:
            db.execute('create table captures(question,state,result)')
            db.execute('insert into captures values(?,?,?)',('小词','completed',json.dumps({
                'availability':'supplement_unavailable','terminal_reason':'card_unavailable'})))
        self.tasks.reconcile()
        daily=self.fixture.current('baidu_ai')['daily']
        self.assertEqual((daily['status'],daily['completed'],daily['unavailable']),('complete_with_unavailable',5,1))
        self.assertEqual(len(self.fixture.system.starts),1)
        self.assertIn('wenxin-card',self.fixture.system.starts[0])

    def test_source_failure_does_not_clear_plan_or_interrupt_worker(self):
        from control_panel import atomic, read
        self.configure()
        self.fixture.system.states['old-baidu_ai.service'] = 'active'
        atomic(self.c.base/'daily_plan.json', {'secondary_monitoring_enabled': True})
        with patch('monthly_monitoring.database_questions', side_effect=TimeoutError): self.tasks.reconcile()
        self.assertEqual(read(self.c.base/'secondary_monitoring_health.json')['status'], 'retrying')
        self.assertEqual(self.fixture.current('baidu_ai')['daily']['config']['secondary_questions'], ['小词'])
        self.assertEqual(self.fixture.system.starts, [])


if __name__ == '__main__': unittest.main()

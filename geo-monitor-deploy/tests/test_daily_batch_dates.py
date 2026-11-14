import json
from pathlib import Path
import tempfile
import unittest
from daily_tasks import belongs_to_daily_plan


class BatchDateTests(unittest.TestCase):
    def test_today_receiving_yesterdays_batch_does_not_satisfy_today(self):
        self.assertFalse(belongs_to_daily_plan('doubao1','geo-panel-doubao1-20261018-090003-abc','2026-10-19',Path('/missing')))
        self.assertTrue(belongs_to_daily_plan('doubao1','geo-panel-doubao1-20261019-090003-abc','2026-10-19',Path('/missing')))

    def test_saved_plan_date_overrides_segment_creation_date(self):
        with tempfile.TemporaryDirectory() as d:
            base=Path(d);jobs=base/'panel/jobs';jobs.mkdir(parents=True)
            batch='geo-panel-doubao2-20261020-000003-abc'
            (jobs/(batch+'.json')).write_text(json.dumps({'daily_date':'2026-10-19'}))
            self.assertTrue(belongs_to_daily_plan('doubao2',batch,'2026-10-19',base))
            self.assertFalse(belongs_to_daily_plan('doubao2',batch,'2026-10-20',base))

    def test_unknown_batch_never_credits_doubao_task(self):
        for batch in ['', '../../secret','unattributed']:
            self.assertFalse(belongs_to_daily_plan('doubao2',batch,'2026-10-19',Path('/missing')))

    def test_other_models_keep_existing_attribution(self):
        self.assertTrue(belongs_to_daily_plan('deepseek2','old-batch','2026-10-19',Path('/missing')))

    def test_managed_web_and_yuanbao_batches_obey_their_plan_dates(self):
        for model in ('wenxin_card','baidu_ai','yuanbao'):
            with self.subTest(model=model):
                batch=f"geo-panel-{model.replace('_','-')}-20261018-090003-abc"
                self.assertFalse(belongs_to_daily_plan(model,batch,'2026-10-19',Path('/missing')))
                self.assertTrue(belongs_to_daily_plan(model,batch,'2026-10-18',Path('/missing')))
                self.assertTrue(belongs_to_daily_plan(model,'manual-batch','2026-10-19',Path('/missing')))


if __name__=='__main__':unittest.main()

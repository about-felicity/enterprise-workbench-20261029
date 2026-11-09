import unittest
from monitor_core.monitoring_scope import scope_fields
from monitor_core.ingestion import normalize_remote_record, normalize_doubao_payload
from monitor_core.analytics import daily_owned_product_recommendations
from monitor_core.recommendation_questions import canonical_recommendation_question
from monitor_core.monthly_keywords import samples


class ScopeTests(unittest.TestCase):
    def test_primary_and_secondary_use_original_not_canonical_category(self):
        self.assertEqual(scope_fields({'prompt':'推荐一款染发剂'})['monitoring_scope'], 'primary')
        record = {'question':'染发剂推荐', 'prompt':'推荐一款植萃染发剂'}
        self.assertEqual(scope_fields(record)['monitoring_scope'], 'secondary')
        self.assertEqual(normalize_remote_record('wenxin', record)['monitoring_scope'], 'secondary')
        self.assertEqual(normalize_doubao_payload({'question':'染发剂推荐','native_result':{'wire_question':'推荐一款植萃染发剂'}}, [])['monitoring_scope'], 'secondary')

    def test_secondary_cannot_enter_primary_performance_denominator(self):
        run = {'question':'染发剂推荐','status':'success','day':'2026-11-09','monitoring_scope':'secondary'}
        self.assertEqual(daily_owned_product_recommendations({'doubao':[run]}, ['doubao']), [])
        run['monitoring_scope']='primary'
        self.assertTrue(daily_owned_product_recommendations({'doubao':[run]}, ['doubao']))

    def test_user_short_product_name_gets_analysis(self):
        self.assertEqual(canonical_recommendation_question('女士防脱精华推荐'), '防脱精华液推荐')

    def test_baidu_and_wenxin_use_same_storage_with_explicit_surface_filter(self):
        class Connection:
            def execute(self, sql, params): self.sql=sql;self.params=params;return []
        c=Connection()
        for model in ('baidu','wenxin','wenxin_all'):
            samples(c,'2026-11-01','2026-12-01',model,{'问题'})
            self.assertEqual(c.params[:2], ('wenxin','wenxin'))
            self.assertEqual(c.params[4:7], (model,model,model))
            self.assertIn("capture_mode", c.sql)


if __name__ == '__main__': unittest.main()

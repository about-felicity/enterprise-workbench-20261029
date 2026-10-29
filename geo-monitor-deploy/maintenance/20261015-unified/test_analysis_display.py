"""Exercise actual API projection without booting database/background workers."""
import ast
from pathlib import Path
import unittest
from unittest.mock import Mock
import threading
from collections import defaultdict

source=Path('geo-monitor-deploy/server-source/doubao_dashboard_server.py').read_text('utf8')
tree=ast.parse(source)
nodes=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in {'_analytics_result_state','_analytics_payload_for_client','_unified_analytics','_unified_analytics_without_coalescing'}]
class Brands:
    def load_settings(self):return {'owned_brands':[]}
namespace={'brand_settings':Brands(),'analytics_valid_brand':lambda x:True,
           'recommendation_body':lambda x:'cleaned','_with_fresh_owned_product_board':lambda r,m:r}
exec(compile(ast.Module(body=nodes,type_ignores=[]),'<api-functions>','exec'),namespace)
class Tests(unittest.TestCase):
    def setUp(self):
        namespace.update(monitor_database=Mock(),_ANALYTICS_CACHE={},_ANALYTICS_BUILDING=set(),
            _ANALYTICS_LOCK=threading.Lock(),_ANALYTICS_KEY_LOCKS=defaultdict(threading.Lock),
            _ANALYTICS_LAST_VALIDATED={},_analytics_content_token=lambda:'token',
            _analytics_data_version=Mock(return_value=1),_load_persisted_unified_analytics=Mock(return_value={'models':[],'old':True}),
            _cache_missing_available_day=lambda *args:False,_schedule_analytics_validation=Mock(),
            _build_interactive_unified_analytics=Mock(return_value={'models':[],'new':True}))
        namespace['monitor_database'].enabled.return_value=True
        namespace['monitor_database'].cache_get.return_value=None
        namespace['_remember_analytics_cache_locked']=lambda key,value:namespace['_ANALYTICS_CACHE'].__setitem__(key,value)
    def test_refresh_is_explicit_and_does_not_mutate_cache(self):
        cached={'generated_at':'yesterday','models':[]}
        result=namespace['_analytics_result_state'](cached,current=False)
        self.assertEqual(result['cache_status']['state'],'refreshing')
        self.assertNotIn('cache_status',cached)
    def test_raw_answer_is_not_replaced_by_analysis_fragment(self):
        raw='完整正文\n\n相关推荐\n仍需可审查的原始捕获'
        result=namespace['_analytics_payload_for_client']({'models':[{'recent_runs':[{'answer':raw}]}]},include_runs=True)
        self.assertEqual(result['models'][0]['recent_runs'][0]['answer'],raw)
        self.assertFalse(result['models'][0]['recent_runs'][0]['answer_trailing_content_removed'])
    def test_unversioned_disk_snapshot_never_served_as_database_current(self):
        result=namespace['_unified_analytics_without_coalescing']({'date':['2026-10-13'],'view':['brands']})
        self.assertTrue(result['new'])
        namespace['_load_persisted_unified_analytics'].assert_not_called()
    def test_stale_memory_is_explicitly_marked_while_refresh_coalesces(self):
        namespace['_ANALYTICS_CACHE'][('','2026-10-13','','brands')]=(0,{'models':[]})
        result=namespace['_unified_analytics']({'date':['2026-10-13'],'view':['brands']})
        self.assertEqual(result['cache_status']['state'],'refreshing')
        namespace['_schedule_analytics_validation'].assert_called_once()
    def test_ingest_between_cache_read_and_validation_does_not_mark_old_payload_current(self):
        namespace['monitor_database'].cache_get.return_value={'models':[]}
        namespace['_analytics_data_version'].side_effect=[1,2]
        result=namespace['_unified_analytics']({'date':['2026-10-13'],'view':['brands']})
        self.assertEqual(result['cache_status']['state'],'refreshing')

if __name__=='__main__':unittest.main()

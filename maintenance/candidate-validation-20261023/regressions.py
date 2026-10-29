import json,shutil,sys,unittest
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated';sys.path[:0]=[str(S/'engine'),str(S)]
modules=['test_api_worker','test_append_repair','test_argument_plan','test_article_allocation','test_article_compiler','test_article_logic','test_article_provenance','test_article_quality','test_auto_repair','test_consumer_voice','test_cost_controls','test_daily_editorial','test_deepseek_api','test_delta_review','test_draft_length','test_editorial','test_execution_runs','test_genre_length','test_genre_pools','test_known_response','test_paragraph_repair','test_preflight_recovery','test_product_identity','test_product_richness','test_reference_design','test_review_genre','test_roster_feature_bullet','test_section_budget_revision','test_arbitration_batches','test_source_analysis','test_source_contract','test_source_scope','test_staged_editorial','test_taxonomy_batches','test_three_agent_quality','test_user_review']
suite=unittest.TestLoader().loadTestsFromNames(['tests.'+m for m in modules])
with (D/'engine-regressions.log').open('w',encoding='utf8') as stream:
 result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
out={'type':'offline_mock_regressions','tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'blocked_network_attempts':len(offline_guard.blocked),'new_api_calls':0}
(D/'engine-regressions.json').write_text(json.dumps(out,indent=2),encoding='utf8');print(json.dumps(out))
sys.exit(not result.wasSuccessful())

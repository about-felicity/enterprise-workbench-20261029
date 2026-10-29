"""Offline regression runner; never contact a model or production data."""
import json
import os
from pathlib import Path
import socket
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT / 'engine'), str(ROOT)]
os.environ['GEO_CREATION_ROOT'] = str(ROOT / 'isolated-runtime')

original_connect = socket.socket.connect
def loopback_only(sock, address):
    if isinstance(address, tuple) and address[0] not in {'127.0.0.1', '::1', 'localhost'}:
        raise RuntimeError('Validation forbids external network access')
    return original_connect(sock, address)
socket.socket.connect = loopback_only

modules = ['tests.test_rewrite_v2', 'tests.test_api_worker', 'tests.test_deepseek_api',
           'tests.test_daily_editorial', 'tests.test_execution_runs', 'tests.test_auto_repair',
           'tests.test_cost_controls', 'tests.test_genre_pools', 'tests.test_three_agent_quality',
           'tests.test_staged_editorial', 'tests.test_word_layout',
           'creation.test_workflow', 'creation.test_studio', 'creation.test_download_service',
           'creation.test_article_export', 'creation.test_worker_recovery', 'creation.test_editorial_health',
           'creation.test_client', 'creation.test_unattended_recovery']
suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
result = unittest.TextTestRunner(verbosity=1).run(suite)
(ROOT / 'verification.json').write_text(json.dumps({
    'tests_run': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors),
    'skipped': len(result.skipped), 'python': sys.version, 'platform': sys.platform,
    'success': result.wasSuccessful(), 'network': 'only loopback allowed',
    'real_model_calls': 0, 'modules': modules}, ensure_ascii=False, indent=2), encoding='utf8')
raise SystemExit(0 if result.wasSuccessful() else 1)

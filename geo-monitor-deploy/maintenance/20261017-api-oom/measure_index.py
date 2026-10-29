import importlib.util
import json
import resource
import time
from pathlib import Path

spec = importlib.util.spec_from_file_location('activity_index', '/tmp/geo_oom_source_activity_index_1017.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
start = time.monotonic()
entries = module.read_activity_entries(Path('/opt/monitor/doubao_source_content_index.json'))
print(json.dumps({'entries': len(entries), 'seconds': round(time.monotonic()-start, 2),
                  'peak_rss_mb': round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
                  'ok': sum(x['status'] == 'ok' for x in entries.values()),
                  'marked': sum(isinstance(x.get('own_product_mentions'), list) for x in entries.values())}))

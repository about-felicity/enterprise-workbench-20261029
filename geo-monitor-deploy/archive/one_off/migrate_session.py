"""Idle, read-only source session check and in-memory seed into the GEO copy."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json
import os
from pathlib import Path
import time
from geo_source_cards.runtime import process_lock, atomic_json
from web_collectors.collector import BrowserCollector

SOURCE = Path('/home/user/geo-editorial/runtime-api/collectors/deepseek')
DEST = Path('/opt/monitor/geo-capture/batches/geo-deepseek-21x3-20261015/collector')


def main():
    with process_lock(SOURCE / 'collector.lock'):
        os.environ['GEO_COLLECTOR_RUNTIME'] = str(SOURCE)
        os.environ['GEO_DEEPSEEK_PORT'] = '9414'
        source = BrowserCollector('deepseek', headless=True)
        try:
            state = source.check_ready()
            print(json.dumps({'source_ready': state.get('ok'), 'source_status': state.get('status')}, ensure_ascii=False), flush=True)
            if not state.get('ok'):
                atomic_json(DEST.parent / 'session_migration.json', {'source_status': state.get('status'), 'at': time.time()})
                return 2
            cookies = source.page.call('Network.getAllCookies')['cookies']
            storage = source.page.evaluate('({local_storage:{...localStorage},session_storage:{...sessionStorage}})')
        finally:
            source.close()
    os.environ['GEO_COLLECTOR_RUNTIME'] = str(DEST)
    os.environ['GEO_DEEPSEEK_PORT'] = '9514'
    os.environ['MONITOR_DEEPSEEK_COOKIES_JSON'] = json.dumps(cookies)
    os.environ['MONITOR_DEEPSEEK_STORAGE_JSON'] = json.dumps(storage)
    with process_lock(DEST / 'collector.lock'):
        target = BrowserCollector('deepseek', headless=True)
        try:
            state = target.check_ready()
            result = {'source_ready': True, 'target_ready': state.get('ok'), 'target_status': state.get('status'), 'at': time.time()}
            atomic_json(DEST.parent / 'session_migration.json', result)
            print(json.dumps(result), flush=True)
            return 0 if state.get('ok') else 2
        finally:
            target.close()
            for name in ('MONITOR_DEEPSEEK_COOKIES_JSON', 'MONITOR_DEEPSEEK_STORAGE_JSON'):
                os.environ.pop(name, None)


if __name__ == '__main__':
    raise SystemExit(main())

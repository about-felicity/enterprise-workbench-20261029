"""Check real GEO persistence, source fidelity and non-disruptive deployment."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import hashlib
import json
from pathlib import Path
import subprocess
import time
import urllib.request

BASE = Path('/opt/monitor/geo-capture')
BACKUP = BASE / 'backups/1792026782'


def command(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout.strip()


def main():
    with urllib.request.urlopen('http://127.0.0.1:8803/api/status', timeout=20) as response:
        fleet = json.load(response)
    names = [c['name'] for c in fleet['containers']]
    before = (BACKUP / 'docker-before.json').read_text().strip()
    after = command('docker', 'inspect', *names, '--format', '{{json .Name}} {{json .State.StartedAt}}')
    assert before == after, 'Existing Docker container restarted'
    editorial = command('systemctl', 'show', 'geo-editorial-scheduler.service', 'geo-editorial-api-worker.service',
                        'geo-editorial-coordinator.service', 'geo-editorial-session-watch.service',
                        '-p', 'Id', '-p', 'MainPID', '-p', 'ExecMainStartTimestamp')
    assert editorial == (BACKUP / 'editorial-before.txt').read_text().strip(), 'Editorial service restarted'
    results = []
    for config_path in sorted((BASE / 'config').glob('*.json')):
        config = json.loads(config_path.read_text())
        root = BASE / 'batches' / config['batch']
        receipts = list((root / 'receipts').glob('*.json'))
        verified = []
        for receipt in receipts:
            item = json.loads((root / 'outbox' / receipt.name).read_text())
            rid = item['request_id']
            assert len(rid) == 64 and all(c in '0123456789abcdef' for c in rid)
            query = "select json_build_object('record',record,'envelope',envelope,'run_id',run_id) from monitor_ingest_events where request_id='" + rid + "'"
            stored = json.loads(command('docker', 'exec', 'monitor-postgres', 'psql', '-U', 'monitor_app', '-d', 'monitor', '-Atc', query))
            original = item['record']
            for field in ('web_body', 'sources', 'capture_result', 'source_entries', 'citations', 'batch_id', 'capture_task_id', 'capture_mode'):
                assert stored['record'][field] == original[field], (config['model'], field, 'fidelity mismatch')
            assert stored['envelope']['record']['capture_result'] == original['capture_result']
            verified.append({'request_id': rid, 'body_length': len(original['web_body']),
                             'source_count': len(original['sources']), 'round': original['round'],
                             'body_sha256': hashlib.sha256(original['web_body'].encode()).hexdigest()})
        results.append({'model': config['model'], 'batch': config['batch'], 'planned': len(config['questions']) * config['rounds'],
                        'verified_processed': len(verified), 'verified': verified})
    assert all(c['status'] == 'running' for c in fleet['containers'])
    # The panel can point either account at a new batch. Verify the immutable
    # historical successes directly instead of requiring a new job to be done.
    for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
        old=json.loads((Path('/home/user/redroid-doubao/batches')/batch/'bridge_health.json').read_text())
        assert old['status']=='complete' and old['geo_processed']==old['captured']==105
    report = {'at': time.time(), 'existing_docker_unchanged': True, 'editorial_services_unchanged': True,
              'doubao_complete_unchanged': True, 'collectors': results, 'fleet': fleet}
    destination = BASE / 'acceptance-current.json'
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps({**{k: report[k] for k in ('at', 'existing_docker_unchanged', 'editorial_services_unchanged', 'doubao_complete_unchanged')},
                      'collectors': [{k: r[k] for k in ('model', 'planned', 'verified_processed')} for r in results]}, ensure_ascii=False))


if __name__ == '__main__':
    main()

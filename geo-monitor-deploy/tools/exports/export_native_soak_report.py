"""Read-only final audit and credential-free export of the authorized test."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0, '/opt/monitor/geo-capture')
from native_soak import audit, read, summarize_queue, NATIVE

TEST = 'doubao-soak2h-1792030883'
BASE = Path('/opt/monitor/geo-capture')
ROOT = BASE/'soak'/TEST
OUT = Path('/home/user/redroid-doubao')/(TEST+'-export')
BACKUP = BASE/'backups/1792026782'

def command(*args):
    return subprocess.run(args, capture_output=True, text=True, check=True, timeout=30).stdout.strip()

def stamp(epoch):
    return datetime.fromtimestamp(epoch, timezone(timedelta(hours=8))).isoformat(timespec='seconds')

manifest = read(ROOT/'manifest.json')
report = read(ROOT/'report.json')
assert manifest['test_id'] == report['test_id'] == TEST
assert manifest['duration_seconds'] == 7200
assert manifest['deadline']-manifest['started_at'] == 7200
assert report['status'] == 'complete' and report['finished_at'] >= manifest['deadline']
metrics = [json.loads(line) for line in (ROOT/'metrics.jsonl').read_text().splitlines()]
verified = [json.loads(line) for line in (ROOT/'verified.jsonl').read_text().splitlines()]
assert len({v['request_id'] for v in verified}) == len(verified)
counts = Counter(v['model'] for v in verified)
models = {}
for model, job in manifest['jobs'].items():
    batch_root = NATIVE/job['batch']
    checked = audit(job, set())
    expected = report['models'][model]
    assert {v['request_id'] for v in checked} == {v['request_id'] for v in verified if v['model'] == model}
    assert len(checked) == counts[model] == expected['captured'] == expected['processed']
    queue = summarize_queue(batch_root/'tasks.sqlite')
    with closing(sqlite3.connect((batch_root/'tasks.sqlite').as_uri()+'?mode=ro', uri=True)) as db:
        clicks = [r[0] for r in db.execute("select time from events where event='send_click_intent_committed' order by time")]
        states = dict(db.execute('select state,count(*) from tasks group by state'))
        after_deadline = []
        for task_id, click_at in db.execute("select task_id,time from events where event='send_click_intent_committed' and time>=?", (manifest['deadline'],)):
            intent = db.execute("select max(time) from events where task_id=? and event='send_intent_committed' and time<=?", (task_id,click_at)).fetchone()[0]
            after_deadline.append({'click_seconds_after_deadline':click_at-manifest['deadline'],
                'send_intent_seconds_before_deadline':manifest['deadline']-intent if intent else None})
    pause = read(ROOT/'operations'/(model+'-pause.json'))
    models[model] = {
        **expected, 'final_reaudit_database_records': len(checked),
        'first_click_beijing': stamp(clicks[0]), 'last_click_beijing': stamp(clicks[-1]),
        'send_span_seconds': clicks[-1]-clicks[0],
        'clicks_after_deadline': sum(t >= manifest['deadline'] for t in clicks),
        'queue_states_now': states, 'pause_operation_recorded': 'result' in pause,
        'deadline_click_evidence': after_deadline,
        'body_characters': sum(v['body_length'] for v in checked),
        'source_entries': sum(v['source_count'] for v in checked), **queue,
    }
    assert queue['send_clicks'] == len(checked) and not queue['duplicate_native_requests']
    assert queue['min_send_interval'] >= 30 and not queue['failed_attempts']

fleet = read(BASE/'fleet.json')
docker_after = command('docker','inspect',*fleet['containers'],'--format','{{json .Name}} {{json .State.StartedAt}}')
before = dict(json.loads('['+line.replace(' ', ',', 1)+']') for line in (BACKUP/'docker-before.json').read_text().strip().splitlines())
after = dict(json.loads('['+line.replace(' ', ',', 1)+']') for line in docker_after.splitlines())
unchanged = {k: after.get(k) == v for k,v in before.items()}
editorial_after = command('systemctl','show','geo-editorial-scheduler.service','geo-editorial-api-worker.service',
    'geo-editorial-coordinator.service','geo-editorial-session-watch.service','-p','Id','-p','MainPID','-p','ExecMainStartTimestamp')
historical = []
for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
    value = read(NATIVE/batch/'bridge_health.json')
    historical.append({'batch':batch,'captured':value['captured'],'processed':value['geo_processed'],
        'unchanged_105':value['captured']==value['geo_processed']==105 and value['status']=='complete'})
summary = {
    'test_id':TEST, 'verified_at_beijing':stamp(time.time()), 'verdict':report['verdict'],
    'started_at_beijing':stamp(manifest['started_at']), 'deadline_beijing':stamp(manifest['deadline']),
    'finished_at_beijing':stamp(report['finished_at']), 'scheduled_seconds':7200,
    'elapsed_including_drain_seconds':report['finished_at']-manifest['started_at'],
    'drain_seconds':report['finished_at']-manifest['deadline'], 'samples':len(metrics),
    'max_sample_gap_seconds':max(b['at']-a['at'] for a,b in zip(metrics,metrics[1:])),
    'models':models, 'verified_total':len(verified), 'all_records_reaudited_against_postgres':True,
    'database_fields_compared':['question','answerText','items','citations','search_queries','native_result','batch_id','round'],
    'deadline_pause':read(ROOT/'deadline_pause.json'), 'anomalies':report['anomalies'],
    'container_start_unchanged':unchanged,
    'non_frontend_containers_unchanged':all(v for k,v in unchanged.items() if k!='/monitor-dashboard'),
    'frontend_restart_note':'Frontend intentionally replaced for user-authorized dashboard and public-prefix integration; capture and analysis containers unchanged.',
    'editorial_services_unchanged':editorial_after==(BACKUP/'editorial-before.txt').read_text().strip(),
    'historical_doubao':historical,
    'scope_note':'Two new native capture batches only; processed confirms capture ingestion, not downstream product AI completion. Emulators remain running; only these batches are paused.',
}
OUT.mkdir(mode=0o755, exist_ok=True)
for name in ('report.json','status.json','metrics.jsonl','verified.jsonl','deadline_pause.json'):
    shutil.copyfile(ROOT/name,OUT/name)
    (OUT/name).chmod(0o644)
(OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
(OUT/'summary.json').chmod(0o644)
print(json.dumps(summary,ensure_ascii=False,indent=2))

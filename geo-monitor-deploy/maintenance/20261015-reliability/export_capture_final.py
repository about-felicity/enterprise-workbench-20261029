"""Read-only adjudication of manifest-owned batches after the fixed deadline.

Never launches, resumes, pauses, or sends a model request. Export files only.
The original recorder's raw evidence remains intact, including counter mixing
after an operator replaces a panel lane with an unrelated batch.
"""
from pathlib import Path
from collections import Counter
from contextlib import closing
from datetime import datetime, timezone, timedelta
import hashlib, json, sqlite3, subprocess, sys, time, zipfile
sys.path.insert(0, '/opt/monitor/geo-capture')
from native_soak import API, read, lane
from all_channel_soak import audit, audit_nontext, job_root, queue_metrics, NATIVE, BUSY

BASE = Path('/opt/monitor/geo-capture')
TEST = 'question-only-soak12h-rowidfix-1792072084'
p = read(BASE / 'soak12h_current.json')
root = Path(p['root'])
m = read(root / 'manifest.json')
assert p['test_id'] == m['test_id'] == TEST
assert time.time() >= m['deadline'] and m['duration_seconds'] == 43200
panel = API().panel()
metrics = [json.loads(s) for s in (root / 'metrics.jsonl').read_text().splitlines() if s.strip()]
marker = read(root / 'deadline_pause.json')
out = Path('/tmp/geo-capture-final-export')
out.mkdir(exist_ok=True, mode=0o755)
def state(unit):
    return subprocess.run(['systemctl', 'is-active', unit], text=True, capture_output=True).stdout.strip()
def bj(t):
    return datetime.fromtimestamp(t, timezone(timedelta(hours=8))).isoformat(timespec='milliseconds')
models = {}
verified = {}
for model, job in m['jobs'].items():
    home = job_root(model, job['batch'])
    current = lane(panel, model)['current']
    superseded = current['batch'] != job['batch']
    unit = ('geo-native@' if model in NATIVE else 'geo-web@') + job['batch'] + '.service'
    original_service = state(unit)
    assert original_service not in BUSY, (model, original_service)
    health = read(home / 'bridge_health.json')
    assert health.get('batch') == job['batch']
    old = next(s['models'][model] for s in reversed(metrics)
               if s.get('models', {}).get(model, {}).get('batch') == job['batch'])
    counts = {k: (current if not superseded else old)[k]
              for k in ('captured', 'processed', 'unique_processed', 'duplicates', 'unavailable')}
    assert counts['captured'] == counts['processed']
    assert health.get('progress', {}).get('pending_delivery', 0) == 0
    receipts = audit(model, job, set())
    assert len(receipts) == counts['unique_processed']
    verified[model] = receipts
    baseline = m['window_baseline'][model]
    window = {k: counts[k] - baseline.get(k, 0) for k in counts}
    window['verified_unique_receipts'] = len(receipts) - baseline['verified_unique_receipts']
    qm = queue_metrics(model, job, m['started_at'])
    dbpath = home / ('tasks.sqlite' if model in NATIVE else 'collector/tasks.sqlite')
    with closing(sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True)) as db:
        if model in NATIVE:
            states = dict(db.execute('select state,count(*) from tasks group by state'))
            non_question = db.execute('select count(*) from tasks where question<>wire_question').fetchone()[0]
            starts = [r[0] for r in db.execute("select time from events where event='send_click_intent_committed' and time>=? and time<=? order by time", (m['started_at'], m['deadline']))]
        else:
            states = dict(db.execute('select state,count(*) from captures group by state'))
            non_question = 0
            starts = [r[0] for r in db.execute('select started from captures where started>=? and started<=? order by started', (m['started_at'], m['deadline']))]
    assert not non_question
    assert not any(states.get(s, 0) for s in ('capturing', 'sending', 'awaiting_ack'))
    after_start = [s for s in metrics if s.get('models', {}).get(model, {}).get('batch') == job['batch']]
    blocked_samples = [s['at'] for s in after_start if s['models'][model].get('state') in ('needs_attention', 'waiting_login')]
    models[model] = {
        'batch': job['batch'], 'baseline': {k: baseline.get(k, 0) for k in counts},
        'batch_cumulative': counts, 'window_delta': window,
        'completed_body_all_sources_citations_raw_PG_fidelity': True,
        'verified_unique_receipts': len(receipts), 'original_service_state': original_service,
        'original_health_state': health.get('status'), 'original_queue_states': states,
        'pending_delivery': health.get('progress', {}).get('pending_delivery', 0),
        'non_question_prompt_rows': non_question, 'queue_metrics_since_window_start': qm,
        'planned_window_send_starts': len(starts),
        'planned_window_min_start_interval': min((b-a for a,b in zip(starts, starts[1:])), default=None),
        'configured_interval': m['original'][model]['settings']['interval'],
        'first_blocked_sample_at': min(blocked_samples, default=None),
        'superseded_by_operator': superseded,
        'current_unrelated_batch': current['batch'] if superseded else None,
        'current_unrelated_service_state': current['service_state'] if superseded else None,
        'deadline_result': marker['results'][model],
        'nontext_audit': audit_nontext(model, job) if model == 'yuanbao' else None,
    }
    if model == 'baidu_ai':
        reasons = Counter()
        with closing(sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True)) as db:
            for raw, in db.execute("select result from captures where state='completed'"):
                r = json.loads(raw)
                if r.get('availability') in ('supplement_unavailable', 'no_card'):
                    reason = r.get('error') or r.get('reason') or r.get('body') or 'unclassified'
                    reasons[str(reason)] += 1
        models[model]['unavailable_reasons'] = dict(reasons)
    if superseded:
        models[model]['old_batch_pause_marker'] = read(home / 'pause.json')

samples_in_window = [s for s in metrics if s.get('at', 0) <= m['deadline']]
first_after = next((s for s in metrics if s.get('at', 0) >= m['deadline']), None)
gaps = [b['at'] - a['at'] for a,b in zip(metrics, metrics[1:])]
gap_max = max(gaps, default=0)
gap_index = gaps.index(gap_max) if gaps else None
deadline_unit = p['deadline_timer'].replace('.timer', '.service')
deadline_execution = subprocess.check_output(['systemctl', 'show', deadline_unit, '-p', 'ExecMainStartTimestamp', '-p', 'ExecMainExitTimestamp', '-p', 'Result'], text=True).strip()
containers_before = dict(line.split(' ', 1) for line in m['docker_before'].splitlines())
containers_now_text = subprocess.check_output(['docker', 'inspect', *m['containers'], '--format', '{{.Name}} {{.State.StartedAt}}'], text=True).strip()
containers_now = dict(line.split(' ', 1) for line in containers_now_text.splitlines())
container_changes = {name: {'before': old, 'after': containers_now.get(name)} for name, old in containers_before.items() if old != containers_now.get(name)}
finished = time.time()
report = {
    'test_id': TEST, 'status': 'complete', 'verdict': 'failed',
    'adjudication_scope': 'Manifest-owned original batches only; all are inactive/failed and have zero delivery backlog. No request or worker mutation performed by this exporter.',
    'started_at': m['started_at'], 'deadline': m['deadline'], 'final_audit_at': finished,
    'started_beijing': bj(m['started_at']), 'deadline_beijing': bj(m['deadline']), 'final_audit_beijing': bj(finished),
    'planned_window_seconds': 43200, 'recorder_last_sample_elapsed_seconds': metrics[-1]['at'] - m['started_at'],
    'first_post_deadline_sample_at': first_after.get('at') if first_after else None,
    'first_post_deadline_sample_elapsed_seconds': first_after['at'] - m['started_at'] if first_after else None,
    'models': models, 'raw_recorder_status': read(root / 'status.json'),
    'metrics': {'total_samples': len(metrics), 'samples_at_or_before_deadline': len(samples_in_window),
                'first_at': metrics[0]['at'], 'last_at': metrics[-1]['at'], 'max_gap_seconds': gap_max,
                'max_gap_from': metrics[gap_index]['at'] if gap_index is not None else None,
                'max_gap_to': metrics[gap_index+1]['at'] if gap_index is not None else None,
                'sample_error_counts': dict(Counter(s.get('error_kind') for s in metrics if s.get('error_kind')))},
    'anomalies': read(root / 'status.json').get('anomalies', []),
    'independent_deadline_execution': deadline_execution, 'latest_deadline_marker': marker,
    'container_changes_against_manifest': container_changes,
    'known_operator_frontend_rebuilds': ['2026-10-16 09:21 no-quark-20261016', '2026-10-16 09:33 board-layout-20261016'],
    'limitations': [
        'This is not six-channel continuous 12-hour collection success. Both Doubao lanes and Yuanbao have unresolved original requests; original DeepSeek was login-blocked and later superseded.',
        'Six completed transient-error attempts and six tasks with two clicks are retained; no claim of zero failures or one click for every task.',
        'Doubao1 captured delta 571 versus processed delta 572 includes one carry-in receipt; do not call all processed deltas newly sent questions.',
        'Baidu full observations, unique processed receipts, duplicate observations and unavailable page observations are separate.',
        'A new DeepSeek batch started by the operator is excluded; the deadline deliberately skips it.',
        'Raw recorder counters after the DeepSeek switch mix the current panel lane with the old manifest. This report reconstructs old-batch counters from last matching samples and independently audits its original receipts.',
        'The raw recorder waits for the unrelated new active lane; this independent final audit instead verifies all original batch services and queues without stopping that new lane.',
        'Client SSH monitoring failed during the 08:04 heartbeat; recorder gaps and sample errors are reported separately, without inventing a successful client audit.',
        'Structural and source fidelity does not establish perpetual semantic correctness; pending analyses and incomplete answers are not negative product evidence.'
    ],
}
for name, value in [('CAPTURE_12H_FINAL_20261015.json', report), ('verified-final.json', verified)]:
    target = out / name
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2))
    target.chmod(0o644)
with zipfile.ZipFile(out / 'raw-evidence.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
    for name in ('manifest.json', 'metrics.jsonl', 'verified.jsonl', 'status.json', 'deadline_pause.json', 'continuity_baseline.json'):
        path = root / name
        if path.exists(): archive.write(path, name)
(out / 'raw-evidence.zip').chmod(0o644)
print(json.dumps({'test_id': TEST, 'verdict': report['verdict'], 'metrics': report['metrics'], 'models': models, 'deadline_execution': deadline_execution, 'container_changes': container_changes}, ensure_ascii=False))

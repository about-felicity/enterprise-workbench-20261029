"""Bounded, read-only observation of real overnight production work."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
from zoneinfo import ZoneInfo

ZONE = ZoneInfo('Asia/Shanghai')
BASE = Path('/opt/monitor/geo-content')
OUTPUT = BASE / 'observations/20261021-22'
EXPECTED_DAY = '2026-10-22'
END = datetime(2026, 10, 22, 17, tzinfo=ZONE)
SERVICES = ['geo-daily-dispatch.timer', 'geo-daily-control', 'geo-creation-studio', 'geo-content-worker', 'geo-content-api', 'geo-deepseek-public-ingest', 'geo-deepseek-upload-tunnel']


def read(path):
    return json.loads(path.read_text('utf-8-sig')) if path.exists() else {}


def file_sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def request_state_paths(base=BASE):
    # Logic subcalls have their own durable uncertainty state, nested below review.
    paths = []
    for name in ('quality-repair', 'logic-review', 'logic-revision'):
        paths.extend((base / 'runtime' / name).rglob('api_state.json'))
    paths.extend((base / 'runtime/runs').glob('*/api/runs/*/call/**/api_state.json'))
    paths.extend((base / 'runtime/runs').glob('*/api/runs/*/logic-call/api_state.json'))
    return paths


def evaluate(snapshot, baseline, now):
    problems = []
    for service, status in snapshot['services'].items():
        if status != 'active':
            problems.append('service_inactive:' + service)
    for plan, jobs in snapshot['next_day_jobs'].items():
        dates = Counter((j['date'], j['question']) for j in jobs)
        if any(n > 1 for n in dates.values()):
            problems.append('duplicate_job:' + plan)
    if set(snapshot.get('unknown_request_ids', [])) - set(baseline.get('unknown_request_ids', [])):
        problems.append('new_unresolved_api_request')
    if snapshot['ledger']['total_committed'] > snapshot['daily_budget_cny'] + 1e-8:
        problems.append('daily_budget_exceeded')
    for path, digest in baseline['protected_controls'].items():
        if snapshot['protected_controls'].get(path) != digest:
            problems.append('paused_control_changed:' + path)
    if baseline.get('source_fingerprint') and snapshot.get('source_fingerprint') != baseline['source_fingerprint']:
        problems.append('source_changed_during_observation')
    if snapshot.get('observation_max_gap_seconds', 0) > 35 * 60:
        problems.append('observation_gap_over_35_minutes')
    for plan, record in snapshot['next_day_tasks'].items():
        if record.get('paused') or record.get('error'):
            problems.append('task_requires_attention:' + plan)
    for record in snapshot['job_states']:
        if record['control'].get('paused') and record['day_status'] != 'complete':
            problems.append('job_requires_attention:' + record['job'])
    finished = now >= END
    if finished:
        if snapshot.get('observed_dates') != ['2026-10-21', '2026-10-22']:
            problems.append('missing_cross_day_observation_history')
        for plan in baseline['expected_writing_plans']:
            jobs = snapshot['next_day_jobs'].get(plan, [])
            if not jobs or not all(j['day_status'] == 'complete' for j in jobs):
                problems.append('next_day_creation_not_complete:' + plan)
        if any(r['credited_pg'] < r['target'] for r in snapshot['geo_counts']):
            problems.append('next_day_geo_not_complete')
        if not snapshot['geo_counts']:
            problems.append('next_day_geo_not_observed')
        observed_models = {r['model'] for r in snapshot['geo_counts']}
        for model in baseline.get('expected_geo_models', []):
            if model not in observed_models:
                problems.append('next_day_geo_model_missing:' + model)
    return {'state': 'needs_attention' if problems else 'complete' if finished else 'observing',
            'issues': problems, 'cross_day_passed': finished and not problems,
            'checked_at': now.isoformat(), 'window_end': END.isoformat(),
            'no_automatic_recovery_or_paid_requests': True}


def collect(now):
    today = now.date().isoformat()
    plans = [read(p) for p in (BASE / 'studio/plans').glob('*.json')]
    expected = [p['plan_id'] for p in plans if p.get('enabled') and p.get('frequency', 'daily') == 'daily' and p.get('task_type') != 'capture_only' and p.get('start_date', today) <= EXPECTED_DAY]
    next_jobs = {}
    states = []
    for path in (BASE / 'runtime/runs').glob('*/job.json'):
        j = read(path)
        if j.get('date') != EXPECTED_DAY:
            continue
        d = read(path.parent / 'days' / EXPECTED_DAY / 'day.json')
        record = {'job': path.parent.name, 'date': j['date'], 'question': j.get('question'), 'day_status': d.get('status'), 'control': read(path.parent / 'control.json')}
        states.append(record)
        next_jobs.setdefault(j.get('studio_plan_id', ''), []).append(record)
    tasks = {p.stem: read(p) for p in (BASE / 'studio/days' / EXPECTED_DAY).glob('*.json')}
    tasks = {k: {n: v.get(n) for n in ('date', 'paused', 'error', 'status', 'jobs')} for k, v in tasks.items()}
    controls = {}
    candidates = [BASE / 'runtime/control.json', Path('/home/user/geo-editorial/runtime-api/control.json')]
    candidates += list((BASE / 'runtime/runs').glob('*/control.json'))
    for path in candidates:
        if read(path).get('paused'):
            controls[str(path)] = file_sha(path)
    services = {n: subprocess.run(['systemctl', 'is-active', n], text=True, capture_output=True).stdout.strip() for n in SERVICES}
    with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro', uri=True) as db:
        charged, reserved = db.execute('select coalesce(sum(charged),0),coalesce(sum(case when charged is null then reserved else 0 end),0) from costs where date=?', (today,)).fetchone()
        unresolved = db.execute('select count(*) from costs where charged is null').fetchone()[0]
    unknown = set()
    paths = request_state_paths()
    paths += list(Path('/home/user/geo-editorial/runtime-api/api/runs').glob('*/call/**/api_state.json'))
    paths += list(Path('/home/user/geo-editorial/runtime-api/api/runs').glob('*/logic-call/api_state.json'))
    for path in paths:
        state = read(path)
        if state.get('state') == 'REQUEST_UNKNOWN' or (state.get('state') == 'HTTP_REJECTED' and state.get('http_status', 0) >= 500):
            unknown.add(state.get('reservation') or str(path))
    settings = read(Path('/home/user/geo-editorial/runtime-api/settings.json'))
    geo = []
    # Existing count helper performs SELECTs against the monitored PostgreSQL data.
    import sys
    sys.path.insert(0, '/opt/monitor/geo-capture')
    from daily_tasks import database_counts
    counts = database_counts(today)
    with sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        for r in db.execute('select model,status,config from daily_tasks where day=?', (today,)):
            cfg = json.loads(r['config']); rounds = cfg.get('rounds', 0); questions = cfg.get('questions', [])
            geo.append({'model': r['model'], 'status': r['status'], 'target': len(questions) * rounds, 'credited_pg': sum(min(counts.get(r['model'], {}).get(q, 0), rounds) for q in questions)})
    expected_geo = read(Path('/opt/monitor/geo-capture/daily_plan.json')).get('models', [])
    source_paths = sorted((BASE / 'creation').glob('*.py')) + sorted((BASE / 'engine/geo_source_cards').glob('*.py'))
    source_fingerprint = hashlib.sha256(''.join(str(p) + file_sha(p) for p in source_paths).encode()).hexdigest()
    timestamps = []
    for path in OUTPUT.glob('2026*.json'):
        value = read(path).get('at')
        if value:
            timestamps.append(datetime.fromisoformat(value))
    timestamps = sorted(timestamps + [now])
    gaps = [(b - a).total_seconds() for a, b in zip(timestamps, timestamps[1:])]
    return {'at': now.isoformat(), 'services': services, 'expected_writing_plans': expected, 'expected_geo_models': expected_geo,
            'protected_controls': controls, 'next_day_jobs': next_jobs, 'next_day_tasks': tasks, 'job_states': states,
            'ledger': {'date': today, 'charged': charged, 'outstanding_reserved_today': reserved, 'total_committed': charged + reserved, 'unresolved': unresolved}, 'unknown_request_ids': sorted(unknown),
            'daily_budget_cny': settings['daily_budget_cny'], 'geo_counts': geo, 'source_fingerprint': source_fingerprint,
            'observed_dates': sorted({d.date().isoformat() for d in timestamps}), 'observation_max_gap_seconds': max(gaps, default=0)}


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    now = datetime.now(ZONE)
    OUTPUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot = collect(now)
    baseline_path = OUTPUT / 'baseline.json'
    if not baseline_path.exists():
        # Exclusive creation prevents concurrent runs from resetting the baseline.
        with baseline_path.open('x', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
    baseline = read(baseline_path)
    result = evaluate(snapshot, baseline, now)
    snapshot['assessment'] = result
    text = json.dumps(snapshot, ensure_ascii=False, indent=2)
    (OUTPUT / (now.strftime('%Y%m%dT%H%M%S') + '.json')).write_text(text, encoding='utf-8')
    temporary = OUTPUT / 'latest.tmp'
    temporary.write_text(text, encoding='utf-8')
    temporary.replace(OUTPUT / 'latest.json')
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()

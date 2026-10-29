"""Close only the expired test recorder after independent original-batch audit."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, subprocess, sys, time, zipfile
sys.path.insert(0, '/opt/monitor/geo-capture')
from native_soak import read, API, lane
from all_channel_soak import BUSY
base = Path('/opt/monitor/geo-capture')
p = read(base / 'soak12h_current.json')
test = 'question-only-soak12h-rowidfix-1792072084'
assert p['test_id'] == test and time.time() >= p['deadline']
root = Path(p['root'])
out = Path('/tmp/geo-capture-final-export')
r = read(out / 'CAPTURE_12H_FINAL_20261015.json')
assert r['test_id'] == test and r['verdict'] == 'failed'
def state(unit):
    return subprocess.run(['systemctl', 'is-active', unit], text=True, capture_output=True).stdout.strip()
panel = API().panel()
before = {}
for model, value in r['models'].items():
    unit = ('geo-native@' if model in {'doubao1','doubao2','yuanbao'} else 'geo-web@') + value['batch'] + '.service'
    assert state(unit) not in BUSY
    c = lane(panel, model)['current']
    before[model] = {'batch': c['batch'], 'service_state': c['service_state']}
    if c['batch'] == value['batch']:
        assert c['state'] == 'paused' and c['pending_delivery'] == 0
        assert c['processed'] == value['batch_cumulative']['processed']
assert p['service'] == 'geo-question-only-soak12h-rowidfix-1792072084.service'
subprocess.run(['systemctl', 'stop', p['service']], check=True, timeout=30)
closed = time.time()
assert state(p['service']) == 'inactive'
after_panel = API().panel()
after = {model: {'batch': lane(after_panel,model)['current']['batch'],
                 'service_state': lane(after_panel,model)['current']['service_state']} for model in before}
assert before == after, (before, after)
closure = {'test_id': test, 'at': closed, 'recorder_unit': p['service'], 'recorder_state': 'inactive',
           'action': 'Stopped only the expired monitoring recorder after manifest-owned batch audit; no capture/creation worker stopped by this script.',
           'panel_batch_and_service_states_before': before, 'panel_batch_and_service_states_after': after,
           'raw_recorder_finalization_limit': 'Raw recorder stayed draining because its all-lane busy condition included the operator new DeepSeek batch. Raw evidence retained; independent adjudication closes only original batch scope.'}
metrics = [json.loads(s) for s in (root/'metrics.jsonl').read_text().splitlines() if s.strip()]
r['recorder_closed_at'] = closed
r['recorder_closed_beijing'] = datetime.fromtimestamp(closed, timezone(timedelta(hours=8))).isoformat(timespec='milliseconds')
r['recorder_wall_elapsed_seconds'] = closed - r['started_at']
r['recorder_last_sample_elapsed_seconds'] = metrics[-1]['at'] - r['started_at']
r['recorder_closure'] = closure
r['metrics']['total_samples'] = len(metrics)
r['metrics']['last_at'] = metrics[-1]['at']
r['finalized_by'] = 'Independent manifest-owned batch audit; original supervisor evidence preserved unchanged'
r['raw_recorder_status'] = read(root / 'status.json')
for target, value in [(out/'CAPTURE_12H_FINAL_20261015.json', r), (out/'recorder-closure.json', closure), (root/'final_adjudication.json', r)]:
    target.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    target.chmod(0o644)
with zipfile.ZipFile(out/'raw-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in ('manifest.json','metrics.jsonl','verified.jsonl','status.json','deadline_pause.json','continuity_baseline.json','final_adjudication.json'):
        f=root/name
        if f.exists():z.write(f,name)
(out/'raw-evidence.zip').chmod(0o644)
checksums = {f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file() and f.name!='SHA256.json'}
(out/'SHA256.json').write_text(json.dumps(checksums,indent=2))
(out/'SHA256.json').chmod(0o644)
print(json.dumps({'closure':closure,'metrics':r['metrics'],'recorder_closed_beijing':r['recorder_closed_beijing'],'wall_elapsed':r['recorder_wall_elapsed_seconds'],'sha256':checksums},ensure_ascii=False))

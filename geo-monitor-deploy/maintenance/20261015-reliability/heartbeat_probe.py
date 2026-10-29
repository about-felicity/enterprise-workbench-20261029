"""Compact read-only recorder/timer check; no collector or control mutation."""
from collections import Counter
import json
from pathlib import Path
import subprocess
import time

base=Path('/opt/monitor/geo-capture')
expected={'soak12h_current.json':('question-only-soak12h-rowidfix-1792072084',43200),
          'creation_soak_current.json':('creation-soak6h-rosterfix-1792062355',21600)}
result={'at':time.time(),'tests':{},'confirmed_config_errors':[]}
for name,(identity,duration) in expected.items():
    pointer=json.loads((base/name).read_text());root=Path(pointer['root'])
    manifest=json.loads((root/'manifest.json').read_text());status=json.loads((root/'status.json').read_text())
    if pointer['test_id']!=identity or manifest['duration_seconds']!=duration:
        result['confirmed_config_errors'].append(name+':identity_or_duration_changed')
    metrics=(root/'metrics.jsonl').read_text()
    lines=metrics.splitlines()
    if not metrics.endswith('\n'):lines=lines[:-1]
    latest=json.loads(lines[-1]) if lines else {}
    verified=Counter();seen=set();duplicates=0
    if (root/'verified.jsonl').exists():
        data=(root/'verified.jsonl').read_text();rows=data.splitlines()
        if not data.endswith('\n'):rows=rows[:-1]
        for line in rows:
            value=json.loads(line);key=(value.get('model'),value.get('request_id'))
            duplicates+=key in seen;seen.add(key);verified[value.get('model')]+=1
    report=json.loads((root/'report.json').read_text()) if (root/'report.json').exists() else None
    value={'test_id':pointer['test_id'],'duration_seconds':manifest['duration_seconds'],
        'elapsed_seconds':status.get('elapsed_seconds'),'status':status['status'],
        'status_age':time.time()-status.get('at',0),'anomalies':status.get('anomalies',[]),
        'sample_error_kind':status.get('error_kind'),'metrics_samples':len(lines),
        'latest_metric_age':time.time()-latest.get('at',0),'verified_by_model':dict(verified),
        'duplicate_verified_entries':duplicates,'report_verdict':report.get('verdict') if report else None,
        'units':subprocess.run(['systemctl','is-active',pointer['service'],pointer['deadline_timer']],text=True,capture_output=True).stdout.splitlines()}
    if 'models' in status:value['window_counts']={m:v.get('window_counts',{}) for m,v in status['models'].items()}
    if 'jobs' in status:value['creation']=[{'approved':len(j['approved']),'approved_in_window':len(j['approved_in_window']),
        'unknown_calls':j['unknown_calls'],'worker':j['worker'].get('result',{}).get('status')} for j in status['jobs']]
    result['tests'][name]=value
path=base/'maintenance/20261015-reliability/heartbeat-probe.json'
path.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))

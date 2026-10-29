"""Read-only, allowlisted inspection. Never emit receiver credentials."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json
from pathlib import Path
import subprocess
import urllib.request
from datetime import datetime, timezone, timedelta


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


base = Path('/opt/monitor')
report = {'checked_at': datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')}
report['receivers'] = {}
for name, path in [('generic', base/'runtime/lan_result_receiver.json'),
                   ('doubao', base/'doubao_mumu_controller/doubao_lan_receiver_config.json')]:
    value = read(path)
    report['receivers'][name] = {k: value[k] for k in ('host', 'port', 'dashboard_port', 'start_dashboard', 'discovery_port') if k in value}
    report['receivers'][name]['bearer_token_configured'] = bool(value.get('token'))
report['web_channels'] = []
for path in sorted((base/'geo-capture/config').glob('*.json')):
    value = read(path)
    root = base/'geo-capture/batches'/value['batch']
    outboxes = sorted((root/'outbox').glob('*.json'), key=lambda p:p.stat().st_mtime)
    channel = {k: value[k] for k in ('model','device','batch','rounds','interval') if k in value}
    channel.update(question_count=len(value['questions']), unique_sent=len(outboxes),
                   processed_receipts=len(list((root/'receipts').glob('*.json'))))
    if outboxes:
        latest = read(outboxes[-1]); record = latest['record']
        channel['latest'] = {'envelope_fields': sorted(latest), 'record_fields': sorted(record),
            'geo_model': latest['model'], 'source_device': latest['source_device'],
            'capture_mode': record['capture_mode'], 'capture_label': record['capture_label'],
            'round': record['round'], 'body_length': len(record['web_body']),
            'sources': len(record['sources']), 'source_entries':len(record.get('source_entries',[])),
            'citations':len(record.get('citations',[])),
            'expected_source_count': record['expected_source_count'],
            'source_capture_complete': record['source_capture_complete'],
            'body_capture_complete':record['body_capture_complete']}
        rid=latest['request_id']
        assert len(rid)==64 and all(c in '0123456789abcdef' for c in rid)
        sql="SELECT json_build_object('body_matches',record->>'web_body'=envelope->'record'->>'web_body','sources_match',record->'sources'=envelope->'record'->'sources','raw_capture_matches',record->'capture_result'=envelope->'record'->'capture_result','model_id',model_id,'source_device',source_device,'run_id',run_id) FROM monitor_ingest_events WHERE request_id='"+rid+"'"
        stored=subprocess.run(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True,capture_output=True,check=True).stdout.strip()
        channel['latest']['database']=json.loads(stored) if stored else None
        receipt=root/'receipts'/outboxes[-1].name
        if receipt.exists():
            value2=read(receipt); analysis=value2.get('analysis',{})
            channel['latest']['receipt']={k:analysis[k] for k in ('answer_length','source_count','expected_source_count','body_capture_complete','source_capture_complete','product_review_status','quarantined') if k in analysis}
    report['web_channels'].append(channel)
with urllib.request.urlopen('http://127.0.0.1:8803/api/status',timeout=20) as response:
    fleet=json.load(response)
report['status_fields']=list(fleet)
report['soak']=read(base/'geo-capture/soak_current.json')
print(json.dumps(report,ensure_ascii=False,indent=2))

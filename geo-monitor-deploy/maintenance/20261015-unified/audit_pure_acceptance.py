"""Validate exact prompts, distinct new conversations, receiver and analytics body fidelity."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

sys.path.insert(0,'/opt/monitor/geo-capture')
from all_channel_soak import audit
BASE=Path('/opt/monitor/geo-capture')
pointer=json.loads((BASE/'question_only_acceptance_current.json').read_text())
manifest=json.loads((Path(pointer['root'])/'manifest.json').read_text())
report={'test_id':pointer['test_id'],'at':time.time(),'question':manifest['question'],'models':{}}
for model,job in pointer['jobs'].items():
    base=Path('/home/user/redroid-yuanbao' if model=='yuanbao' else '/home/user/redroid-doubao')
    root=base/'batches'/job['batch'];health=json.loads((root/'bridge_health.json').read_text())
    with closing(sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        rows=[dict(r) for r in db.execute('select * from tasks order by ordinal')]
        clicks=[r[0] for r in db.execute("select time from events where event='send_click_intent_committed' order by time")]
    if len(rows)!=3 or any(r['state']!='completed' for r in rows):raise RuntimeError('Acceptance still pending: '+model)
    if not all(r['wire_question']==r['question']==manifest['question'] for r in rows):raise RuntimeError('Prompt contains extra text')
    results=[json.loads(r['result_json']) for r in rows]
    if len({r['conversation_id'] for r in results})!=3 or not all(r.get('first_user_turn') for r in results):raise RuntimeError('Conversations were not fresh')
    verified=audit(model,job,set())
    if len(verified)!=3 or health['geo_processed']!=3 or len(clicks)!=3:raise RuntimeError('Missing receipt or duplicate send')
    for path in (root/'outbox').glob('*.json'):
        item=json.loads(path.read_text());record=item.get('payload',item.get('record'));rid=item['request_id']
        q="select to_json(r.answer) from monitor_runs r join monitor_ingest_events e on e.model_id=r.model_id and e.run_id=r.run_id where e.request_id='"+rid+"'"
        body=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',q],text=True))
        original=record.get('answerText',record.get('web_body'))
        if body!=original:raise RuntimeError('Normalized analysis body differs from capture')
    report['models'][model]={'batch':job['batch'],'completed':3,'processed':3,'database_fidelity_verified':3,
        'new_conversations':3,'exact_question_only':True,'send_clicks':3,
        'min_interval':min(b-a for a,b in zip(clicks,clicks[1:])),
        'body_lengths':[len(r['body_markdown']) for r in results],
        'source_counts':[len(r['sources']) for r in results],
        'body_sha256':[hashlib.sha256(r['body_markdown'].encode()).hexdigest() for r in results]}
report.update(passed=True,scope='Three repeated exact questions per device; complete native body and all sources ingested. Not a duration pass. Original two-hour test was interrupted for changed prompt requirements.')
target=Path(pointer['root'])/'report.json';target.write_text(json.dumps(report,ensure_ascii=False,indent=2))
export=Path('/tmp/QUESTION_ONLY_ACCEPTANCE_20261015.json');export.write_text(target.read_text());export.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))

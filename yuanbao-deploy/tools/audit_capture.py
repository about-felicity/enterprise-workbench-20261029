"""Read-only native queue, GEO receipt and PostgreSQL fidelity audit."""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time


def audit(root):
    sys.path.insert(0,'/opt/monitor')
    from monitor_core.recommendation_questions import canonical_recommendation_question
    with closing(sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        db.row_factory=sqlite3.Row
        rows=[dict(r) for r in db.execute("select * from tasks where state='completed' order by ordinal")]
        clicks=[dict(r) for r in db.execute("select task_id,time from events where event='send_click_intent_committed' order by time")]
        states=dict(db.execute('select state,count(*) from tasks group by state'))
    verified=[]
    for path in sorted((root/'receipts').glob('*.json')):
        rid=path.stem
        if not re.fullmatch('[a-f0-9]{64}',rid):raise RuntimeError('Invalid receipt identity')
        item=json.loads((root/'outbox'/path.name).read_text())
        sql="select record from monitor_ingest_events where request_id='"+rid+"'"
        raw=subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True,timeout=30)
        stored=json.loads(raw)
        fields=['prompt','web_body','sources','citations','search_queries','search_queries_exposed','capture_result','source_entries','batch_id','capture_task_id','round','capture_mode']
        expected_question=canonical_recommendation_question(item['record']['question'])
        if stored.get('question')!=expected_question:raise RuntimeError('Configured GEO question normalization mismatch')
        for key in fields:
            if stored.get(key)!=item['record'].get(key):raise RuntimeError('PostgreSQL fidelity mismatch: '+key)
        result=item['record']['capture_result']
        verified.append({'request_id':rid,'task_id':result['task_id'],'conversation_id':result['conversation_id'],
                         'answer_id':result['answer_id'],'body_length':len(result['body_markdown']),
                         'body_sha256':hashlib.sha256(result['body_markdown'].encode()).hexdigest(),
                         'sources':len(result['sources']),'citations':len(result['citations']),
                         'native_eof':result['native_snapshot']['content']['isEof'],
                         'original_prompt_preserved':stored.get('prompt')==item['record']['question'],
                         'search_queries_exposed':result['search_queries_exposed'],'database_fidelity':True})
    gaps=[b['time']-a['time'] for a,b in zip(clicks,clicks[1:])]
    duplicate_clicks=len(clicks)!=len({r['task_id'] for r in clicks})
    duplicate_conversations=len(verified)!=len({r['conversation_id'] for r in verified})
    report={'batch':root.name,'verified_at':time.time(),'states':states,'captured':len(rows),'processed':len(verified),
            'send_clicks':len(clicks),'min_send_interval':min(gaps) if gaps else None,
            'duplicate_send_clicks':duplicate_clicks,'duplicate_conversations':duplicate_conversations,
            'all_processed_database_fidelity':len(verified)==len(rows),
            'body_characters':sum(v['body_length'] for v in verified),'sources':sum(v['sources'] for v in verified),
            'citations':sum(v['citations'] for v in verified),'verified':verified,
            'pause_marker':(root/'maintenance_pause.json').exists(),
            'scope':'Processed confirms capture ingestion. GEO canonicalizes recommendation question labels and preserves the original prompt. Product/source analysis is asynchronous. Native search queries are not exposed; none fabricated.'}
    if duplicate_clicks or duplicate_conversations or any(gap<30 for gap in gaps):raise RuntimeError('Send safety audit failed')
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--batch',default='geo-yuanbao-21x5-20261015');args=p.parse_args()
    if not re.fullmatch('[A-Za-z0-9_-]+',args.batch):raise ValueError('Invalid batch')
    root=Path('/home/user/redroid-yuanbao/batches')/args.batch
    value=audit(root)
    target=root/'capture-audit.json';target.write_text(json.dumps(value,ensure_ascii=False,indent=2));target.chmod(0o600)
    print(json.dumps(value,ensure_ascii=False))

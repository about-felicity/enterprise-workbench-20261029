"""Six-hour real creation/Word/provenance recorder; never starts a collector."""
import argparse
from contextlib import closing
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import time
from geo_source_cards.pipeline_control import pause,state
from geo_source_cards.runtime import atomic_json
from geo_source_cards.writer_handoff import word_matches_draft
from . import runtime

def audit(root):
    job=runtime.read(root/'job.json');manifest=runtime.read(root/'geo_material_manifest.json')
    for observation in manifest['observations']:
        for source in observation['sources']:
            article=source['article'];text=article['text']
            if len(text)!=article['text_length'] or hashlib.sha256(text.encode()).hexdigest()!=article['content_hash']:
                raise ValueError('material_hash_mismatch')
            if not manifest['provenance'].get(source['geo_provenance_key']):raise ValueError('missing_GEO_provenance')
    approved=[]
    for article in runtime.articles(root):
        folder=root/'approved'/article['id'];receipt=runtime.read(folder/'receipt.json')
        review=runtime.read(folder/'semantic_review.json')
        if receipt.get('status')!='accepted_for_user_review' or review.get('failures') or not review.get('checks') or not all(value is True for value in review['checks'].values()):
            raise ValueError('independent_review_not_passed')
        for name,digest in receipt['files'].items():
            if Path(name).name!=name:raise ValueError('unsafe_receipt_file')
            if hashlib.sha256((folder/name).read_bytes()).hexdigest()!=digest:raise ValueError('approved_hash_mismatch')
        check=word_matches_draft(folder/'article.docx',(folder/'draft.md').read_text('utf8'))
        approved.append({'id':article['id'],'word_sha256':receipt['word_sha256'],**check,
                         'independent_review':runtime.read(folder/'semantic_review.json').get('checks')})
    calls=[runtime.read(p) for p in (root/'api/runs').glob('*/call/api_state.json')]
    return {'job_id':job['job_id'],'material_counts':manifest['counts'],'material_hashes_verified':True,
            'approved':approved,'api_calls':len(calls),'unknown_calls':sum(c.get('state') in {'REQUEST_UNKNOWN'} for c in calls),
            'platform_questions_sent':manifest['platform_questions_sent'],'control':state(root),
            'worker':runtime.read(root/'geo_worker.json'),'day':runtime.read(root/'days'/job['date']/'day.json')}

def drain(manifest):
    for identity in manifest['jobs']:
        pause(runtime.job_root(identity),'soak_deadline','六小时测试截止，排空当前API请求；其他任务不受影响')

def run(path,deadline_only=False):
    manifest=runtime.read(path/'manifest.json')
    if deadline_only:
        drain(manifest);atomic_json(path/'deadline_pause.json',{'at':time.time(),'jobs':manifest['jobs']});return
    anomalies=[]
    while True:
        now=time.time();models=[]
        for identity in manifest['jobs']:
            try:
                value=audit(runtime.job_root(identity))
                baseline=set(manifest.get('approved_before',{}).get(identity,[]))
                value['approved_in_window']=[a['id'] for a in value['approved'] if a['id'] not in baseline]
                models.append(value)
            except Exception as error:
                reason=identity+':'+type(error).__name__+':'+str(error)[:150]
                if reason not in anomalies:anomalies.append(reason)
        current={'test_id':manifest['test_id'],'status':'running','at':now,'started_at':manifest['started_at'],
                 'deadline':manifest['deadline'],'elapsed_seconds':now-manifest['started_at'],'jobs':models,'anomalies':anomalies}
        with (path/'metrics.jsonl').open('a') as stream:stream.write(json.dumps(current,ensure_ascii=False)+'\n')
        atomic_json(path/'status.json',current)
        if now>=manifest['deadline']:
            drain(manifest)
            # In-flight calls may finish once; never kill or reset them.
            active=subprocess.run(['systemctl','is-active','geo-content-worker.service'],capture_output=True,text=True).stdout.strip()
            unknown=sum(j['unknown_calls'] for j in models)
            pending=any(runtime.read(runtime.job_root(i)/'api/active.json').get('state') in {'REQUESTING','AUTHORIZING','RESPONDED'} for i in manifest['jobs'])
            # SUBMITTED is durably reconciled; it is safe to retain it for history.
            if pending and now<manifest['deadline']+600:time.sleep(10);continue
            count=sum(len(j['approved']) for j in models)
            new_count=sum(len(j['approved_in_window']) for j in models)
            if unknown:anomalies.append('unknown_api_delivery')
            if pending:anomalies.append('drain_pending_no_forced_kill')
            if not count:anomalies.append('no_approved_actual_articles')
            if not new_count:anomalies.append('no_new_approved_articles_in_test_window')
            if active!='active':anomalies.append('worker_not_active')
            paused=[j['control'] for j in models if j['control'].get('paused') and j['control'].get('reason') not in {'operator','soak_deadline'}]
            if paused:anomalies.append('unresolved_protected_pause')
            current.update(status='complete',finished_at=time.time(),duration_seconds=21600,
                verdict='failed' if anomalies else 'passed',anomalies=anomalies,
                scope='Six-hour service + actual evidence-bound creation, independent review, full Word and GEO provenance. Idle after fixed queue completion is reported; not six continuous hours of paid generation.')
            atomic_json(path/'report.json',current);atomic_json(path/'status.json',current);return
        time.sleep(60)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--deadline-only',action='store_true')
    args=parser.parse_args();run(args.root,args.deadline_only)

"""Durable two-hour native capture test, with graceful deadline pause.

Uses the existing panel operations and separate immutable batches. Does not
reset queues, restart emulators, or interfere with other models/soak recorders.
"""
import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import uuid

import requests

BASE = Path('/opt/monitor/geo-capture')
NATIVE = Path('/home/user/redroid-doubao/batches')
MODELS = ('doubao1', 'doubao2')


def read(path):
    return json.loads(path.read_text('utf-8-sig'))


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    with tmp.open('w', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        __import__('os').fsync(stream.fileno())
    tmp.replace(path)


class API:
    def __init__(self):
        self.session = requests.Session()
        self.session.trust_env = False
        self.url = 'http://127.0.0.1:8803'

    def panel(self):
        result = self.session.get(self.url+'/api/panel', timeout=25)
        result.raise_for_status()
        value = result.json()
        self.csrf = value.pop('csrf')
        return value

    def action(self, model, action, value, key):
        self.panel()
        result = self.session.post(self.url+'/api/control/'+model+'/'+action,
            json=value, headers={'Origin':self.url, 'X-CSRF-Token':self.csrf, 'X-Action-Id':key}, timeout=30)
        result.raise_for_status()
        value = result.json()
        if not value.get('ok'):
            raise RuntimeError('panel_action_not_confirmed')
        return value


def lane(panel, model):
    return next(m for m in panel['models'] if m['id']==model)


def operation(root, api, name, model, action, value):
    path = root/'operations'/(name+'.json')
    if path.exists():
        intent = read(path)
    else:
        intent = {'model':model,'action':action,'value':value,'key':uuid.uuid4().hex}
        atomic(path,intent)
    if 'result' not in intent:
        intent['result'] = api.action(intent['model'],intent['action'],intent['value'],intent['key'])
        atomic(path,intent)
    return intent['result']


def restore(root, api, manifest, model):
    intent_path = root/'operations'/(model+'-settings.json')
    if not intent_path.exists():
        return
    intent = read(intent_path)
    if 'result' not in intent:
        intent['result'] = api.action(model,'settings',intent['value'],intent['key'])
        atomic(intent_path,intent)
    restore_path = root/'operations'/(model+'-restore.json')
    current = lane(api.panel(),model)
    if restore_path.exists() or current['revision']==intent['result']['revision']:
        original = manifest['original'][model]['settings']
        operation(root,api,model+'-restore',model,'settings',
                  {**original,'revision':intent['result']['revision']})
        return True
    # Another operator saved settings: never overwrite them.
    return False


def launch(root, api, manifest):
    for model in MODELS:
        if time.time()>=manifest['deadline']:
            break
        if model in manifest['jobs']:
            restore(root,api,manifest,model)
            continue
        login = operation(root,api,model+'-login',model,'login',{})
        until = min(manifest['deadline'],time.time()+160)
        while time.time()<until:
            state=lane(api.panel(),model)['login_status']['status']
            if state!='checking':break
            time.sleep(2)
        if state!='locally_logged_in':
            raise RuntimeError('native_login_not_ready:'+model)
        original=manifest['original'][model]
        setup=operation(root,api,model+'-settings',model,'settings',
            {**original['settings'],'rounds':20,'revision':original['revision']})
        try:
            if time.time()>=manifest['deadline']:break
            job=operation(root,api,model+'-new',model,'new',{'revision':setup['revision']})
            manifest['jobs'][model]={'batch':job['batch'],'started_at':time.time()}
            atomic(root/'manifest.json',manifest)
        finally:
            restore(root,api,manifest,model)


def recover_jobs(root,manifest):
    # Recover a committed panel operation after the launch response was lost,
    # including when the supervisor restarts after its deadline. No new send.
    for model in MODELS:
        path=root/'operations'/(model+'-new.json')
        if model in manifest['jobs'] or not path.exists():continue
        intent=read(path)
        with closing(sqlite3.connect((BASE/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
            row=db.execute("select result,created from commands where id=? and model=? and action='new'",(intent['key'],model)).fetchone()
        if row:
            result=json.loads(row[0])
            if result.get('batch'):
                manifest['jobs'][model]={'batch':result['batch'],'started_at':row[1]}
                atomic(root/'manifest.json',manifest)


def pause(root, api, manifest):
    results={}
    for model, job in manifest['jobs'].items():
        batch=job['batch']
        if not re.fullmatch(r'geo-panel-doubao[12]-[0-9]{8}-[0-9]{6}-[a-f0-9]{8}',batch):
            raise ValueError('Invalid test batch')
        try:
            current=lane(api.panel(),model)['current']
            if current['batch']!=batch:
                results[model]='superseded_by_operator'
                continue
            if current['state'] in {'paused','stopped','complete'}:
                results[model]=current['state']
                continue
            operation(root,api,model+'-pause',model,'pause',{})
            results[model]='pause_requested'
        except requests.RequestException:
            # Fixed, already registered test batch only. Never kill the worker.
            marker=NATIVE/batch/'maintenance_pause.json'
            if not marker.exists():
                atomic(marker,{'requested_at':time.time(),'source':manifest['test_id'],'action':'pause'})
            results[model]='deadline_marker_written'
    atomic(root/'deadline_pause.json',{'at':time.time(),'results':results})
    return results


def summarize_queue(path):
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        clicks=[r[0] for r in db.execute("select time from events where event='send_click_intent_committed' order by time")]
        minimum=min((b-a for a,b in zip(clicks,clicks[1:])),default=None)
        duplicate=db.execute("select count(*) from (select request_id from tasks where request_id is not null group by request_id having count(*)>1)").fetchone()[0]
        return {'send_clicks':len(clicks),'min_send_interval':minimum,'duplicate_native_requests':duplicate,
                'failed_attempts':db.execute('select count(*) from failed_attempts').fetchone()[0]}


def audit(job, seen):
    root=NATIVE/job['batch'];verified=[]
    for path in sorted((root/'receipts').glob('*.json')):
        if path.stem in seen:continue
        item=read(root/'outbox'/path.name);receipt=read(path)
        rid=item['request_id']
        if not re.fullmatch('[a-f0-9]{64}',rid):raise ValueError('Invalid receipt identity')
        sql="SELECT record FROM monitor_ingest_events WHERE request_id='"+rid+"'"
        stored=subprocess.run(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],capture_output=True,text=True,check=True,timeout=25).stdout.strip()
        if not stored:raise ValueError('processed_without_database_event')
        record=json.loads(stored);original=item['payload']
        for key in ('question','answerText','items','citations','search_queries','native_result','batch_id','round'):
            if record[key]!=original[key]:raise ValueError('database_fidelity_mismatch:'+key)
        analysis=receipt['analysis']
        if receipt['request_id']!=rid or receipt['source_device']!=item['source_device'] or not receipt.get('save',{}).get('run_id'):
            raise ValueError('receipt_identity_mismatch')
        if analysis['answer_length']!=len(original['answerText'].strip()) or analysis['source_count']!=len(original['items']) or not analysis['source_capture_complete']:
            raise ValueError('receipt_completeness_mismatch')
        verified.append({'request_id':rid,'body_length':len(original['answerText']),
            'source_count':len(original['items']),'body_sha256':hashlib.sha256(original['answerText'].encode()).hexdigest(),'at':time.time()})
        seen.add(rid)
    return verified


def sample(api, manifest, seen, root):
    panel=api.panel();results={}
    for model,job in manifest['jobs'].items():
        current=lane(panel,model)['current']
        verified=audit(job,seen[model])
        if verified:
            with (root/'verified.jsonl').open('a',encoding='utf8') as stream:
                for value in verified:stream.write(json.dumps({'model':model,**value})+'\n')
        db=NATIVE/job['batch']/'tasks.sqlite'
        results[model]={k:current[k] for k in ('batch','state','service_state','captured','processed','tasks','delivery_errors','updated_at')}
        results[model].update(verified_receipts=len(seen[model]),**(summarize_queue(db) if db.exists() else {}))
    return results


def run(root):
    manifest=read(root/'manifest.json');api=API()
    recover_jobs(root,manifest)
    seen={m:set() for m in MODELS}
    if (root/'verified.jsonl').exists():
        for line in (root/'verified.jsonl').read_text().splitlines():
            value=json.loads(line);seen[value['model']].add(value['request_id'])
    if time.time()<manifest['deadline']:
        launch(root,api,manifest)
    notes=read(root/'status.json').get('anomalies',[]) if (root/'status.json').exists() else []
    while True:
        draining=time.time()>=manifest['deadline']
        if draining:pause(root,api,manifest)
        models=sample(api,manifest,seen,root)
        for model,value in models.items():
            reason=None
            if value['batch']!=manifest['jobs'][model]['batch']:reason='batch_changed_by_operator'
            elif not draining and time.time()-manifest['started_at']>180 and value['state'] not in {'running','running_backoff','starting'}:
                reason='unexpected_state:'+value['state']
            if reason and model+':'+reason not in notes:notes.append(model+':'+reason)
        status={'test_id':manifest['test_id'],'status':'draining' if draining else 'running',
                'started_at':manifest['started_at'],'deadline':manifest['deadline'],'at':time.time(),'models':models,'anomalies':notes}
        with (root/'metrics.jsonl').open('a',encoding='utf8') as stream:stream.write(json.dumps(status)+'\n')
        atomic(root/'status.json',status)
        if draining and all(m['service_state'] not in {'active','activating','deactivating'} for m in models.values()):
            if set(models)!=set(MODELS):notes.append('missing_test_channel')
            for model,value in models.items():
                if value['verified_receipts']<3:notes.append(model+':insufficient_processed')
                if value.get('min_send_interval') is not None and value['min_send_interval']<30:notes.append(model+':interval_violation')
                if value.get('duplicate_native_requests'):notes.append(model+':duplicate_request')
                if value['state']!='paused' or value['captured']!=value['processed'] or value['delivery_errors']:notes.append(model+':not_cleanly_paused')
            status.update(status='complete',verdict='failed' if notes else 'passed',anomalies=notes,finished_at=time.time())
            atomic(root/'report.json',status);atomic(root/'status.json',status)
            return
        if draining and time.time()>manifest['deadline']+1200:
            status.update(status='needs_attention',reason='drain_timeout_no_forced_stop')
            atomic(root/'status.json',status)
            return
        time.sleep(20)


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--pause-only',action='store_true')
    args=parser.parse_args()
    if args.pause_only:
        manifest=read(args.root/'manifest.json');recover_jobs(args.root,manifest);pause(args.root,API(),manifest)
    else:run(args.root)

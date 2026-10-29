"""Six-channel real capture soak; durable operations and a separate drain deadline."""
import argparse
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time

import requests
from native_soak import API, atomic, lane, operation, read, restore, summarize_queue
from soak_monitor import fidelity

BASE=Path('/opt/monitor/geo-capture')
MODELS=('doubao1','doubao2','yuanbao','deepseek','wenxin_card','baidu_ai')
NATIVE={'doubao1','doubao2','yuanbao'}
BUSY={'active','activating','deactivating'}


def command(*args):
    return subprocess.check_output(args,text=True,timeout=40).strip()


def job_root(model,batch):
    expected='geo-panel-'+model.replace('_','-')+'-'
    if model not in MODELS or not re.fullmatch(re.escape(expected)+r'\d{8}-\d{6}-[a-f0-9]{8}',batch):
        raise ValueError('Unregistered test batch identity')
    base=Path('/home/user/redroid-yuanbao') if model=='yuanbao' else Path('/home/user/redroid-doubao') if model in NATIVE else BASE
    return base/'batches'/batch


def recover(root,manifest):
    for model in MODELS:
        path=root/'operations'/(model+'-new.json')
        if model in manifest['jobs'] or not path.exists():continue
        intent=read(path)
        with closing(sqlite3.connect((BASE/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
            row=db.execute("select result,created from commands where id=? and model=? and action='new'",(intent['key'],model)).fetchone()
        if row:
            batch=json.loads(row[0])['batch'];job_root(model,batch)
            manifest['jobs'][model]={'batch':batch,'started_at':row[1]}
            atomic(root/'manifest.json',manifest)


def pause(root,api,manifest):
    results={}
    for model,job in manifest['jobs'].items():
        target=job_root(model,job['batch'])
        try:
            current=lane(api.panel(),model)['current']
            if current['batch']!=job['batch']:
                results[model]='superseded_by_operator';continue
            if current['service_state'] not in BUSY and current['state'] in {'paused','stopped','complete','complete_with_unavailable'}:
                results[model]=current['state'];continue
            operation(root,api,model+'-pause',model,'pause',{})
            results[model]='pause_requested'
        except requests.RequestException:
            marker=target/('maintenance_pause.json' if model in NATIVE else 'pause.json')
            if not marker.exists():atomic(marker,{'requested_at':time.time(),'source':manifest['test_id'],'action':'pause'})
            results[model]='deadline_marker_written'
    atomic(root/'deadline_pause.json',{'at':time.time(),'results':results})
    return results


def launch(root,api,manifest):
    for model in MODELS:
        if time.time()>=manifest['deadline']:break
        if model in manifest['jobs']:
            restore(root,api,manifest,model);continue
        original=manifest['original'][model]
        setup=operation(root,api,model+'-settings',model,'settings',
                        {**original['settings'],'rounds':manifest.get('capacity_rounds',{}).get(model,20),'revision':original['revision']})
        try:
            if time.time()>=manifest['deadline']:break
            job=operation(root,api,model+'-new',model,'new',{'revision':setup['revision']})
            job_root(model,job['batch'])
            manifest['jobs'][model]={'batch':job['batch'],'started_at':time.time()}
            atomic(root/'manifest.json',manifest)
        finally:restore(root,api,manifest,model)


def verify_receipt_protocol(receipt,item):
    analysis=receipt.get('analysis',{})
    legacy='payload' in item
    original=item['payload'] if legacy else item['record']
    body_complete=(original.get('body_capture_complete') is True and original.get('native_result',{}).get('finished') is True
                   and original.get('complete') is True) if legacy else analysis.get('body_capture_complete') is True
    saved=receipt.get('save',{}).get('run_id') if legacy else receipt.get('stored_run_id')
    if (receipt.get('request_id')!=item['request_id'] or receipt.get('source_device')!=item['source_device']
            or not saved or analysis.get('quarantined') or not body_complete
            or analysis.get('source_capture_complete') is not True):
        raise ValueError('Unproven complete receipt')


def audit(model,job,seen):
    root=job_root(model,job['batch']);pending={}
    for path in (root/'receipts').glob('*.json'):
        if path.stem not in seen:pending[path.stem]=path
    if not pending:return []
    if not all(re.fullmatch('[a-f0-9]{64}',rid) for rid in pending):raise ValueError('Invalid receipt ID')
    sql="select coalesce(json_agg(json_build_object('id',request_id,'record',record)),'[]') from monitor_ingest_events where request_id in ("+','.join("'"+rid+"'" for rid in pending)+')'
    rows=json.loads(command('docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql))
    indexed={r['id']:r['record'] for r in rows};verified=[]
    for rid,path in pending.items():
        item=read(root/'outbox'/path.name);receipt=read(path)
        verify_receipt_protocol(receipt,item)
        analysis=receipt['analysis']
        record=indexed[rid];original=item.get('payload',item.get('record'))
        for key in ('citations','search_queries','search_queries_exposed','batch_id','capture_task_id','round'):
            if key in original and record.get(key)!=original[key]:raise ValueError('Metadata fidelity mismatch: '+key)
        value=fidelity(item,record)
        body=original.get('answerText',original.get('web_body'))
        sources=original.get('items',original.get('sources'))
        if analysis['answer_length']!=len(body.strip()) or analysis['source_count']!=len(sources):
            raise ValueError('Receipt size mismatch')
        if model=='yuanbao' and record['capture_result']!=original['capture_result']:
            raise ValueError('Yuanbao raw native fidelity mismatch')
        value.update(model=model,batch=job['batch'],at=time.time(),database_fidelity=True)
        verified.append(value);seen.add(rid)
    return verified


def audit_nontext(model,job):
    """Audit native video-only events without counting them as text answers."""
    root=job_root(model,job['batch']);paths=list((root/'nontext-receipts').glob('*.json'))
    if not paths:return {'observations':0,'processed':0,'database_fidelity':True}
    if model!='yuanbao' or not all(re.fullmatch('[a-f0-9]{64}',p.stem) for p in paths):
        raise ValueError('Unsupported audit-only receipt identity')
    ids=','.join("'"+p.stem+"'" for p in paths)
    sql="select coalesce(json_agg(json_build_object('id',request_id,'record',record,'run_id',run_id)),'[]') from monitor_ingest_events where model_id='yuanbao' and request_id in ("+ids+')'
    rows=json.loads(command('docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql))
    indexed={r['id']:r for r in rows}
    for path in paths:
        receipt=read(path);item=read(root/'nontext-outbox'/path.name);analysis=receipt['analysis']
        if (receipt.get('request_id')!=item['request_id'] or receipt.get('model')!='yuanbao'
            or receipt.get('source_device')!=item['source_device'] or receipt.get('stored_run_id')
            or analysis.get('quarantined') is not True or analysis.get('answer_present') is not False
            or analysis.get('body_capture_complete') is not False or analysis.get('source_capture_complete') is not False):
            raise ValueError('Invalid non-text audit receipt')
        stored=indexed[item['request_id']];original=item['record']
        if stored['run_id'] or stored['record'].get('web_body') or original.get('web_body'):
            raise ValueError('Video-only audit leaked into text statistics')
        for key in ('capture_result','capture_task_id','batch_id','availability','body_capture_complete','source_capture_complete'):
            if stored['record'].get(key)!=original.get(key):raise ValueError('Non-text raw video fidelity mismatch')
    return {'observations':len(paths),'processed':len(paths),'database_fidelity':True,'scope':'Raw audit events; excluded from full-text counts and product statistics'}


def queue_metrics(model,job,since=None):
    root=job_root(model,job['batch'])
    path=root/'tasks.sqlite' if model in NATIVE else root/'collector/tasks.sqlite'
    if not path.exists():return {}
    if model in NATIVE:
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
            all_starts=[r[0] for r in db.execute("select time from events where event='send_click_intent_committed' order by time")]
            starts=[t for t in all_starts if since is None or t>=since]
            failed_table=db.execute("select 1 from sqlite_master where type='table' and name='failed_attempts'").fetchone()
            value={'send_clicks':len(all_starts),'window_send_clicks':len(starts),'min_send_interval':min((b-a for a,b in zip(starts,starts[1:])),default=None),
                   'batch_min_send_interval':min((b-a for a,b in zip(all_starts,all_starts[1:])),default=None),
                   'duplicate_native_requests':db.execute("select count(*) from (select request_id from tasks where request_id is not null group by request_id having count(*)>1)").fetchone()[0],
                   'failed_attempts':db.execute('select count(*) from failed_attempts').fetchone()[0] if failed_table else 0,
                   'failed_attempts_table_present':bool(failed_table)}
            first,last=min(starts,default=None),max(starts,default=None)
            duplicates=db.execute("select count(*) from (select task_id from events where event='send_click_intent_committed' group by task_id having count(*)>1)").fetchone()[0]
        return {**value,'first_start':first,'last_start':last,'duplicate_send_clicks':duplicates}
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        all_starts=[r[0] for r in db.execute('select started from captures where started is not null order by started')]
        starts=[t for t in all_starts if since is None or t>=since]
        unique_requests=db.execute("select count(*) from (select json_extract(result,'$.url') from captures where state='completed' group by json_extract(result,'$.url') having count(*)>1)").fetchone()[0] if model=='deepseek' else None
        states=dict(db.execute('select state,count(*) from captures group by state'))
    return {'starts':len(all_starts),'window_starts':len(starts),'min_send_interval':min((b-a for a,b in zip(starts,starts[1:])),default=None),
            'batch_min_send_interval':min((b-a for a,b in zip(all_starts,all_starts[1:])),default=None),
            'first_start':min(starts,default=None),'last_start':max(starts,default=None),
            'duplicate_conversations':unique_requests,'queue_states':states,
            'interval_evidence':'capture journal start after rate-slot acquisition; native uses durable click intent'}


def run(root):
    manifest=read(root/'manifest.json');api=API();recover(root,manifest)
    if time.time()<manifest['deadline']:
        try:launch(root,api,manifest)
        except Exception as error:
            recover(root,manifest);pause(root,api,manifest)
            atomic(root/'status.json',{'test_id':manifest['test_id'],'status':'needs_attention',
                'reason':'launch_failed:'+type(error).__name__,'at':time.time(),'jobs':manifest['jobs']})
            return 2
    seen={m:set() for m in MODELS}
    if (root/'verified.jsonl').exists():
        for line in (root/'verified.jsonl').read_text().splitlines():
            value=json.loads(line);seen[value['model']].add(value['request_id'])
    notes=[];sample_failures=0
    if (root/'status.json').exists():notes=read(root/'status.json').get('anomalies',[])
    while True:
        draining=time.time()>=manifest['deadline']
        if draining:pause(root,api,manifest)
        try:
            panel=api.panel();models={}
            for model,job in manifest['jobs'].items():
                current=lane(panel,model)['current']
                for result in audit(model,job,seen[model]):
                    with (root/'verified.jsonl').open('a') as stream:stream.write(json.dumps(result)+'\n')
                value={k:current[k] for k in ('batch','state','service_state','captured','processed','unique_processed','duplicates','unavailable','delivery_errors','updated_at')}
                value.update(verified_unique_receipts=len(seen[model]),**queue_metrics(model,job,manifest['started_at']))
                value['nontext_audit']=audit_nontext(model,job) if model=='yuanbao' else None
                baseline=manifest.get('window_baseline',{}).get(model,{})
                if baseline:
                    value['window_counts']={key:max(0,value.get(key,0)-baseline.get(key,0))
                        for key in ('captured','processed','unique_processed','duplicates','verified_unique_receipts')}
                models[model]=value
                reason=None
                if current['batch']!=job['batch']:reason='batch_changed_by_operator'
                elif not draining and time.time()-job['started_at']>180 and not current['state'].startswith('running') and current['state']!='starting':reason='unexpected_state:'+current['state']
                elif value.get('min_send_interval') is not None and value['min_send_interval']+0.1<manifest['original'][model]['settings']['interval']:reason='interval_violation'
                elif value.get('duplicate_native_requests') or value.get('duplicate_conversations') or value.get('duplicate_send_clicks'):reason='duplicate_request_or_conversation'
                if reason and model+':'+reason not in notes:notes.append(model+':'+reason)
            sample_failures=0
            status={'test_id':manifest['test_id'],'status':'draining' if draining else 'running',
                    'at':time.time(),'started_at':manifest['started_at'],'deadline':manifest['deadline'],
                    'elapsed_seconds':time.time()-manifest['started_at'],'models':models,'anomalies':notes}
        except Exception as error:
            sample_failures+=1
            if sample_failures>=3 and 'sample_failed:'+type(error).__name__ not in notes:notes.append('sample_failed:'+type(error).__name__)
            status={'test_id':manifest['test_id'],'status':'draining' if draining else 'running',
                    'at':time.time(),'error_kind':type(error).__name__,'anomalies':notes}
            models={}
        with (root/'metrics.jsonl').open('a') as stream:stream.write(json.dumps(status)+'\n')
        atomic(root/'status.json',status)
        if draining and set(models)==set(MODELS) and all(v['service_state'] not in BUSY for v in models.values()):
            for model,value in models.items():
                if value['verified_unique_receipts']<3:notes.append(model+':insufficient_unique_processed')
                if manifest.get('window_baseline'):
                    window=value.get('window_counts',{})
                    if window.get('captured',0)<3 or window.get('verified_unique_receipts',0)<3:
                        notes.append(model+':insufficient_new_observations_in_window')
                if value['captured']!=value['processed'] or value['delivery_errors'] or value['state'] not in {'paused','complete','complete_with_unavailable'}:notes.append(model+':not_cleanly_drained')
            after=command('docker','inspect',*manifest['containers'],'--format','{{.Name}} {{.State.StartedAt}}')
            if after!=manifest['docker_before']:notes.append('original_container_restarted')
            continuity_path=root/'continuity_baseline.json'
            continuity={}
            if continuity_path.exists():
                baseline=read(continuity_path)
                current=command('systemctl','show',*baseline['units'],'-p','Id','-p','MainPID','-p','ExecMainStartTimestamp')
                continuity['editorial_tunnel_services_unchanged']=current==baseline['services_before']
                if not continuity['editorial_tunnel_services_unchanged']:notes.append('editorial_or_tunnel_service_restarted')
            historical={}
            for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
                value=read(Path('/home/user/redroid-doubao/batches')/batch/'bridge_health.json')
                historical[batch]={'captured':value.get('captured'),'processed':value.get('geo_processed')}
                if value.get('captured')!=105 or value.get('geo_processed')!=105:notes.append('historical_doubao_changed:'+batch)
            status.update(status='complete',verdict='failed' if notes else 'passed',finished_at=time.time(),anomalies=notes,
                          duration_seconds=manifest['duration_seconds'],jobs=manifest['jobs'],
                          continuity=continuity,historical_doubao=historical)
            atomic(root/'report.json',status);atomic(root/'status.json',status)
            return 0
        if draining and time.time()>manifest['deadline']+1200:
            status.update(status='needs_attention',reason='drain_timeout_no_forced_stop')
            atomic(root/'status.json',status);return 2
        time.sleep(20)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--pause-only',action='store_true');args=parser.parse_args()
    if args.pause_only:
        manifest=read(args.root/'manifest.json');recover(args.root,manifest);pause(args.root,API(),manifest)
    else:sys.exit(run(args.root))

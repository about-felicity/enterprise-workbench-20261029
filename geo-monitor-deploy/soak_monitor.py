"""One-hour read-only soak recorder. Never starts or resets capture tasks."""
from contextlib import closing
import argparse
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import time
import urllib.request

BASE=Path('/opt/monitor/geo-capture')
NATIVE=Path('/home/user/redroid-doubao')


def read(path):return json.loads(path.read_text('utf-8-sig'))
def atomic(path,value):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2))
    temp.replace(path)


def command(*args):return subprocess.run(args,capture_output=True,text=True,check=True,timeout=30).stdout.strip()
def get(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url,timeout=25) as stream:return json.load(stream)


def compact(panel):
    return [{key:value for key,value in {
        'model':m['id'],'batch':m['current']['batch'],'state':m['current']['state'],
        'service_state':m['current']['service_state'],'planned':m['current']['planned'],
        'captured':m['current']['captured'],'processed':m['current']['processed'],
        'unique_processed':m['current']['unique_processed'],'unavailable':m['current']['unavailable'],
        'duplicates':m['current']['duplicates'],'delivery_errors':m['current']['delivery_errors'],
        'updated_at':m['current']['updated_at'],'login':m['login_status']['status']}.items()} for m in panel['models']]


def fidelity(item,stored):
    native='payload' in item
    original=item['payload'] if native else item['record']
    fields=('answerText','items','citations','search_queries','native_result') if native else ('web_body','sources','capture_result','source_entries','citations','batch_id','capture_task_id','capture_mode')
    for key in fields:
        if stored[key]!=original[key]:raise ValueError('capture_fidelity_mismatch:'+key)
    body=original['answerText'] if native else original['web_body']
    sources=original['items'] if native else original['sources']
    return {'request_id':item['request_id'],'body_length':len(body),'sources':len(sources),
            'body_sha256':hashlib.sha256(body.encode()).hexdigest()}


def roots():
    with closing(sqlite3.connect(str(BASE/'panel/control.sqlite'))) as db:
        return [(model,Path(health).parent) for model,health in db.execute('select model,health from jobs')]


def receipts():
    return {p.stem:(model,root,p) for model,root in roots() for p in (root/'receipts').glob('*.json')}


def verify_new(seen):
    new={key:value for key,value in receipts().items() if key not in seen}
    if not new:return []
    ids=list(new)[:100]
    if not all(re.fullmatch('[a-f0-9]{64}',rid) for rid in ids):raise ValueError('invalid_receipt_identity')
    query="select coalesce(json_agg(json_build_object('request_id',request_id,'record',record)),'[]') from monitor_ingest_events where request_id in ("+','.join("'"+rid+"'" for rid in ids)+')'
    records=json.loads(command('docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',query))
    indexed={r['request_id']:r['record'] for r in records}
    verified=[]
    for rid in ids:
        model,root,path=new[rid]
        if rid not in indexed:raise ValueError('processed_receipt_without_database_event')
        item=read(root/'outbox'/path.name)
        result=fidelity(item,indexed[rid])
        result.update(model=model,batch=root.name,at=time.time())
        verified.append(result)
        seen.add(rid)
    return verified


def run(duration):
    start=time.time();begin=time.monotonic()
    test_id=('soak1h-' if duration==3600 else 'recorder-smoke-')+str(int(start))
    out=BASE/'soak'/test_id;out.mkdir(parents=True,mode=0o700)
    fleet=get('http://127.0.0.1:8803/api/status')
    containers=[c['name'] for c in fleet['containers']]
    docker_before=command('docker','inspect',*containers,'--format','{{.Name}} {{.State.StartedAt}}')
    editorial_args=['systemctl','show','geo-editorial-scheduler.service','geo-editorial-api-worker.service',
                    'geo-editorial-coordinator.service','geo-editorial-session-watch.service','-p','Id','-p','MainPID','-p','ExecMainStartTimestamp']
    editorial_before=command(*editorial_args)
    baseline=compact(get('http://127.0.0.1:8803/api/panel'))
    seen=set(receipts())
    previous={(m['model'],m['batch']):m for m in baseline}
    increments={m['model']:{'captured':0,'processed':0,'unique_processed':0,'unavailable':0} for m in baseline}
    notes=[];note_keys=set();verified_total=0;samples=0
    manifest={'test_id':test_id,'started_at':start,'deadline':start+duration,'duration_seconds':duration,
              'baseline':baseline,'scope':'文心/百度连续采集；已完成豆包仅验证保活与历史记录；DeepSeek登录未恢复则列为阻塞'}
    atomic(out/'manifest.json',manifest)
    status={'test_id':test_id,'status':'running','started_at':start,'deadline':start+duration,'samples':0,'report':str(out/'report.json')}
    atomic(BASE/'soak_current.json',status)
    print(json.dumps({'status':'started','test_id':test_id,'started_at':start,'deadline':start+duration}),flush=True)
    def note(kind,model='fleet'):
        key=(kind,model)
        if key not in note_keys:notes.append({'at':time.time(),'kind':kind,'model':model});note_keys.add(key)
    try:
        while True:
            tick=time.monotonic()
            try:
                current=compact(get('http://127.0.0.1:8803/api/panel'))
                available=get('http://127.0.0.1:8803/api/status')
                if any(c['status']!='running' for c in available['containers']):note('container_not_running')
                for m in current:
                    key=(m['model'],m['batch'])
                    old=previous.get(key)
                    for field in increments[m['model']]:
                        difference=m[field]-(old[field] if old else 0)
                        if difference<0:note('counter_decreased',m['model'])
                        else:increments[m['model']][field]+=difference
                    previous[key]=m
                    if m['state'] in {'needs_attention','stale'}:note(m['state'],m['model'])
                    if m['delivery_errors']:note('delivery_error_observed',m['model'])
                verified=verify_new(seen)
                verified_total+=len(verified)
                if verified:
                    with (out/'verified.jsonl').open('a') as stream:
                        for result in verified:stream.write(json.dumps(result,ensure_ascii=False)+'\n')
                sample={'at':time.time(),'elapsed':time.monotonic()-begin,'models':current,'new_verified':len(verified)}
            except Exception as error:
                note('sample_failed:'+type(error).__name__)
                sample={'at':time.time(),'elapsed':time.monotonic()-begin,'error_kind':type(error).__name__}
            with (out/'metrics.jsonl').open('a') as stream:stream.write(json.dumps(sample,ensure_ascii=False)+'\n')
            samples+=1
            status.update(samples=samples,last_sample_at=time.time(),deltas=increments,anomalies=notes,verified_new_receipts=verified_total)
            atomic(BASE/'soak_current.json',status)
            remaining=duration-(time.monotonic()-begin)
            if remaining<=0:break
            time.sleep(min(60,remaining,max(1,60-(time.monotonic()-tick))))
        if command('docker','inspect',*containers,'--format','{{.Name}} {{.State.StartedAt}}')!=docker_before:note('existing_docker_restarted')
        if command(*editorial_args)!=editorial_before:note('editorial_service_restarted')
        for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
            h=read(NATIVE/'batches'/batch/'bridge_health.json')
            if h.get('captured')!=105 or h.get('geo_processed')!=105:note('historical_doubao_changed')
        final=compact(get('http://127.0.0.1:8803/api/panel'))
        blocked=[m['model'] for m in final if m['state']=='waiting_login']
        tested=[m for m in increments if increments[m]['processed']>0]
        for model in ('wenxin_card','baidu_ai'):
            if increments[model]['processed']==0:note('no_processed_progress',model)
        verdict='failed' if notes else 'partial' if blocked else 'passed_available_channels'
        report={**manifest,'finished_at':time.time(),'elapsed_seconds':time.monotonic()-begin,'samples':samples,
                'verdict':verdict,'deltas':increments,'verified_new_receipts':verified_total,
                'tested_capture_channels':tested,'blocked_channels':blocked,'monitor_only':[m for m in ('doubao1','doubao2') if increments[m]['processed']==0],
                'anomalies':notes,'final':final}
        atomic(out/'report.json',report)
        status.update(status='complete',verdict=verdict,finished_at=time.time(),anomalies=notes)
        atomic(BASE/'soak_current.json',status)
        print(json.dumps({'status':'complete','verdict':verdict,'report':str(out/'report.json')}),flush=True)
    except BaseException as error:
        status.update(status='failed',failed_at=time.time(),error_kind=type(error).__name__)
        atomic(BASE/'soak_current.json',status)
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--duration',type=int,default=3600)
    args=parser.parse_args()
    if not 1<=args.duration<=7200:raise SystemExit('Invalid duration')
    run(args.duration)

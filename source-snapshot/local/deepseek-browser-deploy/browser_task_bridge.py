"""Daily task adapter for the persistent MV3 browser; no browser or prompt duplication."""
import argparse,fcntl,hashlib,json,signal,sqlite3,sys,time
from pathlib import Path
import requests
sys.path.insert(0,'/opt/monitor/geo-capture')
from browser_backend import ROOT,atomic,read,command,probe
from runtime_reliability import DeliveryGate
STOP=False
def stop(*_):
    global STOP
    STOP=True

def run(config):
    root=Path('/home/user/redroid-deepseek-account2/batches')/config['batch'];root.mkdir(exist_ok=True)
    with (ROOT/'assignment.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return run_locked(config,root)

def run_locked(config,root):
    expected={'batch':config['batch'],'questions':config['questions'],'rounds':config['rounds']}
    request_key=hashlib.sha256(('browser-start:'+config['batch']).encode()).hexdigest()[:32]
    started=command('start',expected,key=request_key)
    if started.get('ok') is False:raise RuntimeError('browser_start_not_confirmed')
    existing=command('get')
    if existing.get('job',{}).get('state')=='paused' and not (root/'maintenance_pause.json').exists():command('resume',expected)
    run_id=existing.get('job',{}).get('id') or started['job']['id']
    atomic(root/'browser_assignment.json',{'browser_run_id':run_id,**expected})
    db=sqlite3.connect(root/'tasks.sqlite');db.row_factory=sqlite3.Row
    db.execute('create table if not exists tasks(task_id text primary key,ordinal int,question text,state text)')
    schedule=[q for _ in range(config['rounds']) for q in config['questions']]
    for i,q in enumerate(schedule,1):db.execute('insert or ignore into tasks values(?,?,?,?)',(config['batch']+':'+str(i),i,q,'pending'))
    db.commit()
    receiver=read(Path('/opt/monitor/runtime/lan_result_receiver.json'))
    session=requests.Session();session.trust_env=False;session.headers['Authorization']='Bearer '+receiver['token']
    gate=DeliveryGate(root,atomic)
    for name in ('outbox','receipts'):(root/name).mkdir(exist_ok=True)
    while True:
        state=read(ROOT/'state.json');job=state.get('plugin_job') or {};assignment=state.get('assignment') or {}
        if assignment.get('batch')!=config['batch']:time.sleep(2);continue
        results=[]
        path=ROOT/'data/deepseek_results.jsonl'
        if path.exists():
            for line in path.read_text().splitlines():
                try:value=json.loads(line)
                except ValueError:continue
                if value.get('run_id')==run_id:results.append(value)
        good=[];errors=[];processed=0
        for value in results:
            ordinal=int(value['round']);question=schedule[ordinal-1]
            if value.get('prompt')!=question:raise ValueError('browser_question_identity_mismatch')
            valid=(value.get('status')=='success' and bool(value.get('web_body','').strip())
                   and value.get('source_capture_complete') is True
                   and len(value.get('sources',[]))>=int(value.get('expected_source_count',0)))
            if not valid:
                errors.append({'code':'browser_capture_incomplete','ordinal':ordinal,'retryable':False});continue
            good.append(ordinal)
            record={**value,'collector_model':'deepseek','capture_mode':'chromium_headless_extension',
                    'capture_label':'DeepSeek 浏览器插件','body_capture_complete':True,'batch_id':config['batch']}
            device='deepseek-browser-extension'
            raw=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'))
            rid=hashlib.sha256(('deepseek\n'+device+'\n'+raw).encode()).hexdigest()
            item={'version':1,'model':'deepseek','request_id':rid,'source_device':device,'record':record,'sent_at':value['finished_at']}
            outbox=root/'outbox'/(rid+'.json');receipt=root/'receipts'/outbox.name
            if not outbox.exists():atomic(outbox,item)
            if read(outbox)!=item:raise ValueError('frozen_browser_result_changed')
            if not receipt.exists() and gate.due(rid):
                try:
                    response=session.get('http://127.0.0.1:8803/api/receipts/deepseek/'+rid,timeout=8);response.raise_for_status();reply=response.json()
                    if reply.get('status')=='processed':
                        result=reply['receipt'];a=result.get('analysis',{})
                        if (result.get('request_id')!=rid or result.get('source_device')!=device
                            or a.get('answer_length')!=len(record['web_body'].strip()) or a.get('source_count')!=len(record['sources'])
                            or a.get('source_capture_complete') is not True or not result.get('stored_run_id') or a.get('quarantined') is True):
                            raise ValueError('browser_receipt_mismatch')
                        atomic(receipt,result);gate.complete(rid)
                    elif gate.may_post(rid):
                        response=session.post('http://127.0.0.1:'+str(receiver['port'])+'/api/v1/models/deepseek/results',json=item,timeout=10)
                        response.raise_for_status();ack=response.json()
                        if ack.get('request_id')!=rid:raise ValueError('receiver_ack_mismatch')
                        gate.waiting(rid,posted=True)
                except (requests.RequestException,ValueError) as error:errors.append(gate.failed(rid,error))
            if receipt.exists():processed+=1
        inflight=job.get('inFlight') or {};phase=inflight.get('phase','')
        cursor=int(job.get('cursor',0));total=len(schedule)
        with db:
            db.execute("update tasks set state='pending'")
            for i in good:db.execute("update tasks set state='completed' where ordinal=?",(i,))
            if phase in ('submitted','send_intent'):db.execute("update tasks set state='prepared' where ordinal=?",(cursor+1,))
        counts={r[0]:r[1] for r in db.execute('select state,count(*) from tasks group by state')}
        auth=probe()['status'];paused=(root/'maintenance_pause.json').exists() or STOP
        status='running';progress='rate_wait' if state.get('next_send_not_before',0)>time.time()*1000 and phase not in ('submitted','send_intent') else 'generating'
        if errors:status='running_delivery_backoff' if any(e.get('retryable') for e in errors) else 'needs_attention'
        if len(good)>processed:progress='delivery'
        if auth in ('login_required','risk_blocked','verification_required'):status='waiting_login' if auth=='login_required' else 'waiting_verification'
        if paused and phase not in ('submitted','send_intent') and len(good)==processed:
            command('pause',expected);status='maintenance_paused'
        if job.get('state')=='paused' and not paused and status=='running':status='needs_attention'
        complete=job.get('state')=='completed' and processed==total
        if complete:status='complete';progress='complete'
        atomic(root/'bridge_health.json',{'batch':config['batch'],'model':'deepseek2','planned':total,
          'captured':len(good),'geo_processed':processed,'tasks':counts,'delivery_errors':errors,
          'time':time.time(),'heartbeat_expires_at':time.time()+150,'bridge_pid':__import__('os').getpid(),
          'status':status,'progress':{'phase':progress,'ordinal':min(total,cursor+1),'next_at':state.get('next_send_not_before',0)/1000},
          'backend':'browser_extension','browser_run_id':run_id})
        if complete or status=='maintenance_paused':return 0
        if status in ('waiting_login','waiting_verification'):return 77
        if status=='needs_attention':
            if job.get('state')=='running':command('pause',expected)
            return 2
        time.sleep(3)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);args=p.parse_args()
    signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop)
    raise SystemExit(run(read(args.config)))

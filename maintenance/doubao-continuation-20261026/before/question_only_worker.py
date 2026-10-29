"""Exact-question native capture with durable local bindings and first-turn evidence."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import sys
import time

sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_core import Queue,PROTOCOL,source_absence_verified
from unattended_core import DataError,is_transient_error
from unattended_worker import atomic_json, deadline
from question_only_adapters import DoubaoReader,yuanbao_reader,android as make_android
from question_only_delivery import DoubaoDelivery
from runtime_reliability import CompletionFence
from native_readback_guard import AppReadbackGuard
from native_memory_guard import MemoryGuard
sys.path.insert(0,'/home/user/redroid-yuanbao')
from native_core import NativeDataError
from delivery import Delivery
DEVICES={'doubao1':('doubao-hpe14-13-test','127.0.0.1:5557'),
         'doubao2':('doubao-hpe14-account2','127.0.0.1:5558'),
         'yuanbao':('yuanbao-hpe14-android13','127.0.0.1:5559')}
ADB='/home/user/redroid-doubao/linux-tools/platform-tools/adb' 

STOP=False

def stop_signal(*_):
    global STOP
    STOP=True


def wait_seconds(seconds):
    end=time.monotonic()+seconds
    while not STOP and time.monotonic()<end:time.sleep(min(1,max(0,end-time.monotonic())))


def native_auth_required(android,model):
    """Read visible login controls; never infer logout from a transport error."""
    device=getattr(android,'device',None)
    if device is None:return False
    current=device.app_current()
    package='com.tencent.hunyuan.app.chat' if model=='yuanbao' else 'com.larus.nova'
    if not isinstance(current,dict) or current.get('package')!=package:return False
    if model!='yuanbao':
        from question_only_adapters import optional_commerce_login
        if optional_commerce_login(device.dump_hierarchy()):return False
    return any(bool(device(text=text).exists) for text in ('登录','手机号登录','微信扫码登录','安全验证'))


def load_config(path):
    value=json.loads(path.read_text('utf-8-sig'))
    model=value.get('model')
    if model not in DEVICES or value.get('prompt_mode')!='question_only' or not re.fullmatch(r'[A-Za-z0-9_-]{1,180}',value.get('batch','')):
        raise ValueError('Question-only immutable native batch required')
    questions=value['questions'];rounds=value['rounds'];interval=value['interval']
    if not questions or len(questions)>500 or len(set(questions))!=len(questions) or not all(isinstance(q,str) and q and q==q.strip() for q in questions):raise ValueError('Distinct exact questions required')
    if type(rounds) is not int or not 1<=rounds<=200 or type(interval) is not int or not 30<=interval<=3600:raise ValueError('Invalid rounds/send interval')
    container,serial=DEVICES[model]
    return {'model':model,'batch':value['batch'],'questions':questions,'rounds':rounds,'interval':interval,
            'container':container,'serial':serial,'prompt_mode':'question_only'}


def run(config,capture_limit=0):
    base=Path('/home/user/redroid-yuanbao' if config['model']=='yuanbao' else '/home/user/redroid-doubao')
    root=base/'batches'/config['batch'];root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(root,0o700)
    manifest=root/'capture_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=config:raise NativeDataError('Immutable batch settings changed')
    atomic_json(manifest,config)
    lock_name=('redroid-yuanbao-' if config['model']=='yuanbao' else 'redroid-doubao-')+config['container']+'.lock'
    with (Path('/run/lock')/lock_name).open('a') as device_lock,(root/'worker.lock').open('a') as job_lock:
        fcntl.flock(device_lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(job_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return run_locked(config,root,capture_limit)


def run_locked(config,root,capture_limit):
    queue=Queue(root/'tasks.sqlite');os.chmod(queue.path,0o600)
    queue.enqueue(config['batch'],config['questions']*config['rounds'],True)
    reader=yuanbao_reader(root) if config['model']=='yuanbao' else DoubaoReader(root,config['container'])
    delivery=Delivery(root,len(config['questions'])) if config['model']=='yuanbao' else DoubaoDelivery(root,len(config['questions']),config['container'])
    android=None
    fence=CompletionFence()
    app_guard=AppReadbackGuard(root,atomic_json,model=config['model'])
    memory_guard=MemoryGuard(root,config['container'],config['model'],atomic_json)
    last_auth_at=0;last_auth_task=None
    def recovery_event(task_id,name,detail):
        with queue.db:queue.event(task_id,name,detail)
    read_failures=0
    progress={'phase':'starting','changed_at':time.time()}
    def phase(name,task=None,**details):
        nonlocal progress
        identity=task.get('task_id') if task else None
        if (progress.get('phase'),progress.get('task_id'))!=(name,identity):
            progress={'phase':name,'task_id':identity,'ordinal':task.get('ordinal') if task else None,
                      'changed_at':time.time()}
        progress.update(details)
        health.update(progress=progress,time=time.time(),heartbeat_expires_at=max(time.time()+150,details.get('next_at',0)+30))
        atomic_json(root/'bridge_health.json',health)
    health={'batch':config['batch'],'planned':len(config['questions'])*config['rounds'],'prompt_mode':'question_only','model':config['model']}
    terminal='stopped'
    try:
        while True:
            summary=queue.summary()
            try:metrics=delivery.sync(queue)
            except (NativeDataError,DataError) as error:
                health.update(status='running_recovery',delivery_errors=[{'kind':'receipt_validation_failed','code':'receipt_validation_pending','retryable':True}])
                phase('delivery_validation_backoff',next_at=time.time()+60)
                if STOP:return 0
                wait_seconds(60);continue
            metrics['unavailable']=summary.get('completed_nontext',0)
            if capture_limit and summary.get('completed',0)>=capture_limit and not (root/'maintenance_pause.json').exists():
                atomic_json(root/'maintenance_pause.json',{'requested_at':time.time(),'source':'acceptance_limit','action':'pause'})
            paused=(root/'maintenance_pause.json').exists()
            task=queue.next_task()
            if summary.get('needs_attention'):
                row=queue.db.execute("select * from tasks where state='needs_attention' order by rowid limit 1").fetchone()
                task=dict(row)
                # Retry preparation only with durable proof that no send click occurred.
                boundary=queue.attempt_boundary(task['task_id'])
                clicked=queue.db.execute("select 1 from events where task_id=? and event='send_click_intent_committed' and id>?",(task['task_id'],boundary)).fetchone()
                if not clicked and (task['attempts']>0 or queue.may_finish_unsent(task['task_id'])):
                    with queue.db:
                        queue.db.execute("update tasks set state='pending',error=null where task_id=?",(task['task_id'],))
                        queue.event(task['task_id'],'automatic_unsent_preparation_recovery')
                    task=queue.next_task()
            # ready() is explicitly bounded at 75s and send() at 30s. A 45s
            # lease falsely marked a live bounded preparation as stale.
            health.update(metrics,time=time.time(),heartbeat_expires_at=time.time()+150,
                          bridge_pid=os.getpid(),tasks=summary,status='running',delivery_errors=metrics['delivery_errors'])
            if summary.get('needs_attention'):health['status']='running_recovery'
            elif paused:health['status']='pausing'
            elif metrics['geo_processed']!=metrics['captured'] or metrics.get('nontext_pending'):health['status']='running_delivery_backoff'
            if any(e.get('retryable') is False for e in metrics['delivery_errors']):
                health['status']='running_delivery_backoff'
            if memory_guard:health['memory']=memory_guard.refresh()
            atomic_json(root/'bridge_health.json',health)
            if metrics['geo_processed']!=metrics['captured'] or metrics.get('nontext_pending'):
                phase('delivery',pending_delivery=metrics['captured']-metrics['geo_processed']+metrics.get('nontext_pending',0))
                if STOP:break
                wait_seconds(5);continue
            if not task:
                terminal='complete_with_unavailable' if summary.get('completed_nontext') else 'complete';return 0
            if (paused or STOP) and task['state']=='pending':
                terminal='maintenance_paused' if paused else 'stopped';return 0
            try:
                if memory_guard:
                    maintenance=memory_guard.maintain(task,summary,metrics,recovery_event,paused=paused,stopping=STOP)
                    if maintenance:
                        reader.close()
                        health['status']='running_recovery';health['memory']=memory_guard.metrics
                        phase(maintenance.pop('phase'),task,**maintenance)
                        android=None;last_auth_at=0
                        if STOP:return 0
                        wait_seconds(3);continue
                if android is None:
                    android=make_android(config['model'],config['serial'],ADB)
                    last_auth_at=0
                if config['model']=='yuanbao' or task['task_id']!=last_auth_task or time.time()-last_auth_at>=30:
                    from history_refresh import pause_blocks_readback
                    marker=json.loads((root/'maintenance_pause.json').read_text()) if paused else {}
                    if config['model']!='yuanbao' and task.get('request_id') and reader.paths(task)[1].is_file() and not STOP and not (paused and pause_blocks_readback(marker)):
                        from question_only_adapters import dismiss_optional_commerce_login
                        if dismiss_optional_commerce_login(android,lambda:recovery_event(task['task_id'],'native_optional_commerce_login_decline_intent','Decline optional shop connection; App may resume the original question')):
                            recovery_event(task['task_id'],'native_optional_commerce_login_dismissed','Shop connection declined; preserve App continuation provenance')
                    if native_auth_required(android,config['model']):
                        terminal='waiting_login';return 77
                    last_auth_at=time.time();last_auth_task=task['task_id']
                from history_refresh import pause_blocks_readback
                marker=json.loads((root/'maintenance_pause.json').read_text()) if paused else {}
                recovery=app_guard.check(android.device,task,{},recovery_event,
                    paused=paused and pause_blocks_readback(marker),stopping=STOP)
                if recovery:
                    reader.close();health['status']='running_recovery'
                    phase(recovery.pop('phase'),task,**recovery)
                    if STOP:return 0
                    wait_seconds(3);continue
                try:
                    with deadline(30):observed=reader.lookup(task)
                    read_failures=0
                except (NativeDataError,DataError):raise
                except Exception as error:
                    read_failures+=1
                    with queue.db:queue.event(task['task_id'],'read_transport_failure',type(error).__name__+': '+str(error).split('\n')[0][:400])
                    reader.close()  # reconnect only the reader, never restart the App or resend
                    wait=min(300,5*2**min(6,read_failures-1))
                    health['status']='running_recovery'
                    phase('read_backoff',task,next_at=time.time()+wait,attempt=read_failures)
                    if STOP:return 0
                    wait_seconds(wait)
                    continue
                if config['model'] in ('doubao1','doubao2'):
                    from draft_submission_recovery import recover as recover_draft
                    from history_refresh import pause_blocks_readback
                    marker=json.loads((root/'maintenance_pause.json').read_text()) if paused else {}
                    recovery=recover_draft(root,task,observed,android,reader.database_paths(),recovery_event,
                        paused=paused and pause_blocks_readback(marker),stopping=STOP,
                        last_send_path=root.parent.parent/('last_send-'+config['container']+'.json'),interval=config['interval'])
                    if recovery:
                        health['status']='running_recovery';phase(recovery.pop('phase'),task,**recovery)
                        wait_seconds(3);continue
                if config['model']=='yuanbao' and observed.get('status')=='absent' and task['state']=='prepared':
                    from unbound_history import recover as recover_unbound
                    recovery=recover_unbound(root,task,observed,android,reader.close,recovery_event,
                        paused=paused and pause_blocks_readback(marker),stopping=STOP)
                    if recovery:
                        health['status']='running_recovery';phase(recovery.pop('phase'),task,**recovery)
                        wait_seconds(3);continue
                if config['model']=='yuanbao' and observed.get('reason')=='native_history_not_loaded':
                    from history_refresh import restore_after_exit
                    recovery=restore_after_exit(root,task,android,reader.close,recovery_event,reader.history_entries,
                        paused=paused and pause_blocks_readback(marker),stopping=STOP)
                    if recovery:
                        health['status']='running_recovery';phase(recovery.pop('phase'),task,**recovery)
                        wait_seconds(3);continue
                if config['model']=='yuanbao' and observed.get('reason') in {'native_answer_fetch_failed','native_answer_interrupted'}:
                    from history_refresh import refresh_original,pause_blocks_readback
                    marker=json.loads((root/'maintenance_pause.json').read_text()) if paused else {}
                    recovery=refresh_original(root,task,observed,android,reader.close,recovery_event,
                        paused=paused and pause_blocks_readback(marker),stopping=STOP,history_entries=reader.history_entries)
                    if recovery:
                        health['status']='running_recovery';phase(recovery.pop('phase'),task,**recovery)
                        wait_seconds(3);continue
                if (config['model']!='yuanbao' and observed.get('status')=='complete'
                        and task.get('require_sources') and not observed.get('sources')
                        and not is_transient_error(observed) and not source_absence_verified(observed)):
                    observed={**observed,'status':'pending','phase':'awaiting_complete_snapshot','reason':'required_sources_pending'}
                stable=fence.ready(task['task_id'],observed)
                if task['state']=='prepared' and time.time()-(task.get('prepared_at') or time.time())>900 and not stable:
                    health['status']='running_recovery'
                    phase('awaiting_original_result',task,next_at=time.time()+30,reason='original_request_stalled',deadline_at=task['prepared_at']+900)
                    if STOP:return 0
                    wait_seconds(30)
                    continue
                unsent=task['state']=='prepared' and observed['status']=='absent' and queue.may_finish_unsent(task['task_id'])
                if task['state']=='pending' or unsent:
                    if task.get('not_before',0)>time.time():wait_seconds(min(3,task['not_before']-time.time()));continue
                    if observed['status']!='absent':raise NativeDataError('Unsent task already has a native result; inspect before sending')
                    if paused or STOP:
                        # Preparation without a click is still safe to drain.
                        if unsent:
                            with queue.db:
                                queue.db.execute("update tasks set state='pending',prepared_at=null where task_id=?",(task['task_id'],))
                                queue.event(task['task_id'],'pause_before_first_click','Phase-v2 durable evidence proves no send click')
                        terminal='maintenance_paused' if paused else 'stopped';return 0
                    last=queue.db.execute("select max(time) from events where event='send_click_intent_committed'").fetchone()[0] or 0
                    global_marker=root.parent.parent/('last_send-'+config['container']+'.json')
                    if global_marker.exists():last=max(last,json.loads(global_marker.read_text())['time'])
                    remaining=last+config['interval']-time.time()
                    if remaining>0:
                        phase('rate_wait',task,next_at=last+config['interval'])
                        wait_seconds(min(remaining,3));continue
                    if android is None:android=make_android(config['model'],config['serial'],ADB)
                    try:
                        phase('preparing',task)
                        with deadline(75):
                            # NativeClient needs a live App process before its baseline.
                            # Do not call ready() first: it creates a new conversation.
                            if config['model']=='yuanbao':android.ensure_open()
                            reader.before_new_chat(task)
                            android.ready()
                    except Exception as error:
                        print(json.dumps({'event':'preparation_failed','ordinal':task['ordinal'],
                            'error':type(error).__name__,'detail':str(error)[:240] if isinstance(error,DataError) else ''}),flush=True)
                        queue.retry_preparation(task['task_id'],type(error).__name__,limit=None)
                        if native_auth_required(android,config['model']):
                            terminal='waiting_login';return 77
                        android=None
                        health['status']='running_recovery'
                        phase('preparation_backoff',task,next_at=time.time()+30)
                        wait_seconds(30);continue
                    if task['state']=='pending':queue.prepare(task['task_id'],protocol='phase-v2')
                    def commit_click():
                        queue.click_attempt(task['task_id'])
                        atomic_json(global_marker,{'time':time.time(),'task_id':task['task_id'],'batch':config['batch']})
                    try:
                        phase('sending_once',task)
                        with deadline(30):android.send(task['wire_question'],commit_click)
                    except Exception as error:
                        with queue.db:queue.event(task['task_id'],'send_uncertain',type(error).__name__)
                        if queue.may_finish_unsent(task['task_id']):
                            queue.retry_preparation(task['task_id'],type(error).__name__,limit=None)
                    else:
                        with queue.db:queue.event(task['task_id'],'send_tap_returned')
                    continue
                if observed['status'] in {'complete','nontext_complete'}:
                    if config['model']!='yuanbao' and is_transient_error(observed):
                        queue.schedule_transient_retry(task['task_id'],observed,limit=None);continue
                    if not stable:
                        phase('verifying_complete_snapshot',task)
                        wait_seconds(3);continue
                    if observed['status']=='nontext_complete':queue.complete_nontext(task['task_id'],observed)
                    else:queue.complete(task['task_id'],observed,allow_readback=task['state']=='needs_attention')
                    if android:android.evidence(root,task['task_id'])
                    print(json.dumps({'event':'nontext_observed' if observed['status']=='nontext_complete' else 'captured','ordinal':task['ordinal'],'body_length':len(observed['body_markdown']),'sources':len(observed['sources'])}),flush=True)
                    continue
                if observed.get('request_id'):queue.attach_request(task['task_id'],observed['request_id'])
                phase(observed.get('phase') or ('generating' if observed.get('native_request_confirmed') else 'awaiting_ack'),task,
                      reason=observed.get('reason',''),deadline_at=task['prepared_at']+900)
                if STOP:return 0
                wait_seconds(3)
            except (NativeDataError,DataError) as error:
                with queue.db:queue.event(task['task_id'],'native_validation_backoff',type(error).__name__)
                health['status']='running_recovery'
                phase('native_validation_backoff',task,next_at=time.time()+60,reason=str(error)[:240])
                reader.close()
                if STOP:return 0
                wait_seconds(60)
            except Exception as error:
                with queue.db:queue.event(task['task_id'],'infrastructure_error',type(error).__name__)
                reader.close();android=None
                health['status']='running_recovery'
                phase('infrastructure_backoff',task,next_at=time.time()+30)
                if STOP:return 0
                wait_seconds(30)
    finally:
        reader.close()
        health.update(time=time.time(),heartbeat_expires_at=None,bridge_pid=None,status=terminal,tasks=queue.summary())
        atomic_json(root/'bridge_health.json',health)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--capture-limit',type=int,default=0)
    args=parser.parse_args()
    signal.signal(signal.SIGTERM,stop_signal);signal.signal(signal.SIGINT,stop_signal)
    raise SystemExit(run(load_config(args.config),args.capture_limit))

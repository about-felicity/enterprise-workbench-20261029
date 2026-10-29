"""Exact-question native capture with durable local bindings and first-turn evidence."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import random
import signal
import sys
import time

sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_core import Queue,PROTOCOL
from unattended_core import DataError,is_transient_error
from unattended_worker import atomic_json, deadline
from reader import Reader
from android import make_android
from device import auth
from policy import interval_range
from delivery import Delivery
from runtime_reliability import CompletionFence
sys.path.insert(0,'/home/user/redroid-yuanbao')
from native_core import NativeDataError
DEVICES={'deepseek2':('deepseek-hpe14-account2','127.0.0.1:5561')}
ADB='/home/user/redroid-doubao/linux-tools/platform-tools/adb' 

STOP=False

def stop_signal(*_):
    global STOP
    STOP=True


def native_auth_required(android,model):
    """Read visible login controls; never infer logout from a transport error."""
    return auth(android.device)['status']=='login_required'


def load_config(path):
    value=json.loads(path.read_text('utf-8-sig'))
    model=value.get('model')
    if model not in DEVICES or value.get('prompt_mode')!='question_only' or not re.fullmatch(r'[A-Za-z0-9_-]{1,180}',value.get('batch','')):
        raise ValueError('Question-only immutable native batch required')
    questions=value['questions'];rounds=value['rounds'];interval=value['interval']
    if not questions or len(questions)>500 or len(set(questions))!=len(questions) or not all(isinstance(q,str) and q and q==q.strip() for q in questions):raise ValueError('Distinct exact questions required')
    if type(rounds) is not int or not 1<=rounds<=200:raise ValueError('Invalid rounds')
    interval_range(interval)
    container,serial=DEVICES[model]
    return {'model':model,'batch':value['batch'],'questions':questions,'rounds':rounds,'interval':interval,
            'container':container,'serial':serial,'prompt_mode':'question_only',**({'private_root':value['private_root']} if value.get('private_root') else {})}


def run(config,capture_limit=0):
    base=Path('/home/user/redroid-deepseek-account2')
    root=Path(config['private_root'])/'native' if config.get('private_root') else base/'batches'/config['batch'];root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(root,0o700)
    manifest=root/'capture_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=config:raise NativeDataError('Immutable batch settings changed')
    atomic_json(manifest,config)
    lock_name='redroid-deepseek-'+config['container']+'.lock'
    with Path('/opt/monitor/geo-capture/deepseek2_account.lock').open('a') as account_lock,(Path('/run/lock')/lock_name).open('a') as device_lock,(root/'worker.lock').open('a') as job_lock:
        fcntl.flock(account_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.flock(device_lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(job_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return run_locked(config,root,capture_limit)


def run_locked(config,root,capture_limit):
    queue=Queue(root/'tasks.sqlite');os.chmod(queue.path,0o600)
    queue.enqueue(config['batch'],config['questions']*config['rounds'],True)
    reader=Reader(root)
    delivery=Delivery(root,config)
    android=None
    fence=CompletionFence()
    read_failures=0
    progress={'phase':'starting','changed_at':time.time()}
    def phase(name,task=None,**details):
        nonlocal progress
        identity=task.get('task_id') if task else None
        if (progress.get('phase'),progress.get('task_id'))!=(name,identity):
            progress={'phase':name,'task_id':identity,'ordinal':task.get('ordinal') if task else None,
                      'changed_at':time.time()}
        progress.update(details)
        health.update(progress=progress,time=time.time(),heartbeat_expires_at=time.time()+150)
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
                time.sleep(60);continue
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
            atomic_json(root/'bridge_health.json',health)
            if metrics['geo_processed']!=metrics['captured'] or metrics.get('nontext_pending'):
                phase('delivery',pending_delivery=metrics['captured']-metrics['geo_processed']+metrics.get('nontext_pending',0))
                if STOP:break
                time.sleep(5);continue
            if not task:
                terminal='complete_with_unavailable' if summary.get('completed_nontext') else 'complete';return 0
            if (paused or STOP) and task['state']=='pending':
                terminal='maintenance_paused' if paused else 'stopped';return 0
            try:
                if android is None:
                    android=make_android(config['model'],config['serial'],ADB)
                if native_auth_required(android,config['model']):
                    terminal='waiting_login';return 77
                try:
                    with deadline(30):observed=reader.lookup(task)
                    read_failures=0
                except (NativeDataError,DataError):raise
                except Exception as error:
                    read_failures+=1
                    with queue.db:queue.event(task['task_id'],'read_transport_failure',type(error).__name__)
                    reader.close()  # reconnect only the reader, never restart the App or resend
                    wait=min(300,5*2**min(6,read_failures-1))
                    health['status']='running_recovery'
                    phase('read_backoff',task,next_at=time.time()+wait,attempt=read_failures)
                    if STOP:return 0
                    time.sleep(wait)
                    continue
                if (config['model']!='yuanbao' and observed.get('status')=='complete'
                        and task.get('require_sources') and not observed.get('sources')
                        and not is_transient_error(observed)):
                    observed={**observed,'status':'pending','phase':'awaiting_complete_snapshot','reason':'required_sources_pending'}
                stable=fence.ready(task['task_id'],observed)
                if task['state']=='prepared' and time.time()-(task.get('prepared_at') or time.time())>900 and not stable:
                    health['status']='running_recovery'
                    phase('awaiting_original_result',task,next_at=time.time()+30)
                    if STOP:return 0
                    time.sleep(30)
                    continue
                unsent=task['state']=='prepared' and observed['status']=='absent' and queue.may_finish_unsent(task['task_id'])
                if task['state']=='pending' or unsent:
                    if task.get('not_before',0)>time.time():time.sleep(min(3,task['not_before']-time.time()));continue
                    if observed['status']!='absent':raise NativeDataError('Unsent task already has a native result; inspect before sending')
                    if paused or STOP:
                        # Preparation without a click is still safe to drain.
                        if unsent:
                            with queue.db:
                                queue.db.execute("update tasks set state='pending',prepared_at=null where task_id=?",(task['task_id'],))
                                queue.event(task['task_id'],'pause_before_first_click','Phase-v2 durable evidence proves no send click')
                        terminal='maintenance_paused' if paused else 'stopped';return 0
                    last=queue.db.execute("select max(time) from events where event='send_click_intent_committed'").fetchone()[0] or 0
                    global_marker=Path('/opt/monitor/geo-capture/deepseek2_last_send.json')
                    if global_marker.exists():
                        rate=json.loads(global_marker.read_text());last=max(last,rate.get('time',0),rate.get('last_prompt_epoch',0))
                    else:rate={}
                    minimum,maximum=interval_range(config['interval'])
                    next_send=max(last+minimum,rate.get('next_send_epoch',0)) if last else 0
                    remaining=next_send-time.time()
                    if remaining>0:
                        phase('rate_wait',task,next_at=next_send)
                        time.sleep(min(remaining,3));continue
                    if android is None:android=make_android(config['model'],config['serial'],ADB)
                    try:
                        phase('preparing',task)
                        with deadline(75):
                            reader.before_new_chat(task)
                            android.ready()
                    except Exception as error:
                        reason=str(error) if isinstance(error,DataError) else type(error).__name__
                        queue.retry_preparation(task['task_id'],reason,limit=None)
                        if native_auth_required(android,config['model']):
                            terminal='waiting_login';return 77
                        android=None
                        health['status']='running_recovery'
                        phase('preparation_backoff',task,next_at=time.time()+30,reason=reason)
                        time.sleep(30);continue
                    if task['state']=='pending':queue.prepare(task['task_id'],protocol='phase-v2')
                    def commit_click():
                        queue.click_attempt(task['task_id'])
                        now=time.time();delay=random.SystemRandom().randint(minimum,maximum)
                        atomic_json(global_marker,{'time':now,'last_prompt_epoch':now,'next_send_epoch':now+delay,'interval_seconds':delay,'task_id':task['task_id'],'batch':config['batch']})
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
                        time.sleep(3);continue
                    if observed['status']=='nontext_complete':queue.complete_nontext(task['task_id'],observed)
                    else:queue.complete(task['task_id'],observed,allow_readback=task['state']=='needs_attention')
                    if android:android.evidence(root,task['task_id'])
                    print(json.dumps({'event':'nontext_observed' if observed['status']=='nontext_complete' else 'captured','ordinal':task['ordinal'],'body_length':len(observed['body_markdown']),'sources':len(observed['sources'])}),flush=True)
                    continue
                if observed.get('request_id'):queue.attach_request(task['task_id'],observed['request_id'])
                phase(observed.get('phase') or ('generating' if observed.get('native_request_confirmed') else 'awaiting_ack'),task,
                      reason=observed.get('reason',''),deadline_at=task['prepared_at']+900)
                if STOP:return 0
                time.sleep(3)
            except (NativeDataError,DataError) as error:
                with queue.db:queue.event(task['task_id'],'native_validation_backoff',type(error).__name__)
                health['status']='running_recovery'
                phase('native_validation_backoff',task,next_at=time.time()+60,reason=str(error))
                reader.close()
                if STOP:return 0
                time.sleep(60)
            except Exception as error:
                with queue.db:queue.event(task['task_id'],'infrastructure_error',type(error).__name__)
                reader.close();android=None
                health['status']='running_recovery'
                phase('infrastructure_backoff',task,next_at=time.time()+30)
                if STOP:return 0
                time.sleep(30)
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

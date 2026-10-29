"""Headless Yuanbao capture with the proven Doubao durable send protocol."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import sys
import time

sys.path.insert(0,'/home/user/redroid-doubao')
from unattended_core import Queue,DataError
from unattended_worker import atomic_json, deadline
from android_ui import Android
from native_client import NativeClient, BASE
from native_core import NativeDataError
from delivery import Delivery

STOP=False

def stop_signal(*_):
    global STOP
    STOP=True


def load_config(path):
    value=json.loads(path.read_text('utf-8-sig'))
    if value.get('model')!='yuanbao' or not re.fullmatch(r'[A-Za-z0-9_-]{1,180}',value.get('batch','')):
        raise ValueError('Invalid Yuanbao batch')
    questions=value['questions'];rounds=value['rounds'];interval=value['interval']
    if not questions or len(questions)>500 or len(set(questions))!=len(questions) or not all(isinstance(q,str) and q.strip() for q in questions):raise ValueError('Distinct questions required')
    if type(rounds) is not int or not 1<=rounds<=20 or type(interval) is not int or not 30<=interval<=3600:raise ValueError('Invalid rounds/send interval')
    return {'model':'yuanbao','batch':value['batch'],'questions':questions,'rounds':rounds,'interval':interval,
            'container':'yuanbao-hpe14-android13','serial':'127.0.0.1:5559'}


def run(config,capture_limit=0):
    root=BASE/'batches'/config['batch'];root.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(root,0o700)
    manifest=root/'capture_manifest.json'
    if manifest.exists() and json.loads(manifest.read_text())!=config:raise NativeDataError('Immutable batch settings changed')
    atomic_json(manifest,config)
    with Path('/run/lock/redroid-yuanbao-yuanbao-hpe14-android13.lock').open('a') as device_lock,(root/'worker.lock').open('a') as job_lock:
        fcntl.flock(device_lock,fcntl.LOCK_EX|fcntl.LOCK_NB);fcntl.flock(job_lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return run_locked(config,root,capture_limit)


def run_locked(config,root,capture_limit):
    queue=Queue(root/'tasks.sqlite');os.chmod(queue.path,0o600)
    queue.enqueue(config['batch'],config['questions']*config['rounds'],True)
    reader=NativeClient(root);delivery=Delivery(root,len(config['questions']));android=None
    health={'batch':config['batch'],'planned':len(config['questions'])*config['rounds']}
    terminal='stopped'
    try:
        while True:
            summary=queue.summary()
            try:metrics=delivery.sync(queue)
            except NativeDataError as error:
                terminal='needs_attention'
                health.update(delivery_errors=[{'kind':'receipt_validation_failed'}])
                atomic_json(root/'maintenance_pause.json',{'requested_at':time.time(),'source':'receipt_validation','action':'pause'})
                return 2
            if capture_limit and summary.get('completed',0)>=capture_limit and not (root/'maintenance_pause.json').exists():
                atomic_json(root/'maintenance_pause.json',{'requested_at':time.time(),'source':'acceptance_limit','action':'pause'})
            paused=(root/'maintenance_pause.json').exists()
            task=queue.next_task()
            health.update(metrics,time=time.time(),heartbeat_expires_at=time.time()+45,
                          bridge_pid=os.getpid(),tasks=summary,status='running',delivery_errors=metrics['delivery_errors'])
            if summary.get('needs_attention'):health['status']='needs_attention'
            elif paused:health['status']='pausing'
            elif metrics['geo_processed']!=metrics['captured']:health['status']='running_delivery_backoff'
            atomic_json(root/'bridge_health.json',health)
            if metrics['geo_processed']!=metrics['captured']:
                if STOP:break
                time.sleep(5);continue
            if summary.get('needs_attention'):
                terminal='needs_attention';return 2
            if not task:
                terminal='complete';return 0
            if (paused or STOP) and task['state']=='pending':
                terminal='maintenance_paused' if paused else 'stopped';return 0
            try:
                if android is None:
                    android=Android()
                    with deadline(45):android.ensure_open()
                observed=reader.lookup(task)
                unsent=task['state']=='prepared' and observed['status']=='absent' and queue.may_finish_unsent(task['task_id'])
                if task['state']=='pending' or unsent:
                    if observed['status']!='absent':raise NativeDataError('Unsent task already has a native result; inspect before sending')
                    if paused or STOP:
                        # Preparation without a click is still safe to drain.
                        if unsent:
                            with queue.db:
                                queue.db.execute("update tasks set state='pending',prepared_at=null where task_id=?",(task['task_id'],))
                                queue.event(task['task_id'],'pause_before_first_click','Phase-v2 durable evidence proves no send click')
                        terminal='maintenance_paused' if paused else 'stopped';return 0
                    last=queue.db.execute("select max(time) from events where event='send_click_intent_committed'").fetchone()[0] or 0
                    global_marker=BASE/'last_send.json'
                    if global_marker.exists():last=max(last,json.loads(global_marker.read_text())['time'])
                    remaining=last+config['interval']-time.time()
                    if remaining>0:time.sleep(min(remaining,3));continue
                    if android is None:android=Android()
                    try:
                        with deadline(60):android.ready()
                    except Exception as error:
                        queue.retry_preparation(task['task_id'],type(error).__name__+': '+str(error) if isinstance(error,NativeDataError) else type(error).__name__)
                        time.sleep(5);continue
                    if task['state']=='pending':queue.prepare(task['task_id'],protocol='phase-v2')
                    def commit_click():
                        queue.click_attempt(task['task_id'])
                        atomic_json(global_marker,{'time':time.time(),'task_id':task['task_id'],'batch':config['batch']})
                    try:
                        with deadline(30):android.send(task['wire_question'],commit_click)
                    except Exception as error:
                        with queue.db:queue.event(task['task_id'],'send_uncertain',type(error).__name__)
                        if queue.may_finish_unsent(task['task_id']):
                            queue.retry_preparation(task['task_id'],type(error).__name__)
                    else:
                        with queue.db:queue.event(task['task_id'],'send_tap_returned')
                    continue
                if observed['status']=='complete':
                    queue.complete(task['task_id'],observed)
                    if android:android.evidence(root,task['task_id'])
                    print(json.dumps({'event':'captured','ordinal':task['ordinal'],'body_length':len(observed['body_markdown']),'sources':len(observed['sources'])}),flush=True)
                    continue
                if observed.get('request_id'):queue.attach_request(task['task_id'],observed['request_id'])
                if time.time()-task['prepared_at']>900:
                    queue.attention(task['task_id'],'Native send/answer unresolved; automatic resend forbidden')
                time.sleep(3)
            except (NativeDataError,DataError) as error:
                queue.attention(task['task_id'],str(error))
            except Exception as error:
                with queue.db:queue.event(task['task_id'],'infrastructure_error',type(error).__name__)
                # Retain prepared click intent and original task for restart.
                raise
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

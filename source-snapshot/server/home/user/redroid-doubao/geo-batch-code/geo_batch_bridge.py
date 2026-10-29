"""Persistent Doubao capture and authenticated, idempotent GEO delivery."""
import hashlib
import os
import json
import subprocess
import sys
import time
import signal
from pathlib import Path
from datetime import datetime, timezone, timedelta
import requests
from unattended_core import Queue
from unattended_worker import atomic_json

BASE = Path('/home/user/redroid-doubao')
BATCH = os.environ.get('DOUBAO_BATCH', 'geo-products-21x5-20261013')
CONTAINER = os.environ.get('DOUBAO_CONTAINER', 'doubao-hpe14-13-test')
SERIAL = os.environ.get('DOUBAO_SERIAL', '127.0.0.1:5557')
STATE = BASE/'batches'/BATCH
RECEIVER = Path('/opt/monitor/doubao_mumu_controller/doubao_lan_receiver_config.json')


def record_shutdown(state, worker_exit=None, reason='bridge_exit'):
    path = state/'bridge_health.json'
    health = json.loads(path.read_text()) if path.exists() else {}
    health.update(time=time.time(), stopped_at=time.time(),
                  worker_exit=worker_exit if worker_exit is not None else health.get('worker_exit'),
                  stop_reason=reason, bridge_pid=None, heartbeat_expires_at=None)
    if health.get('status') != 'complete':
        health['status'] = 'needs_attention' if health.get('tasks',{}).get('needs_attention') else 'stopped'
    atomic_json(path,health)


def stop_signal(signum, frame):
    raise SystemExit(0)


def envelope(task, completed_at, question_count=21):
    result = json.loads(task['result_json'])
    from question_only_core import source_absence_verified
    if not result['finished'] or not result['body_markdown'].strip() or (not result['sources'] and not source_absence_verified(result)):
        raise ValueError('Full answer and sources required')
    identity = hashlib.sha256(('redroid-doubao:'+task['task_id']+':'+str(result['request_id'])).encode()).hexdigest()
    captured = datetime.fromtimestamp(completed_at,timezone(timedelta(hours=8))).isoformat()
    payload = {'question':task['question'], 'answerText':result['body_markdown'],
        'url':'https://www.doubao.com/chat/'+str(result['conversation_id']),
        'items':result['sources'], 'citations':result['citations'], 'search_queries':result['search_queries'],
        'count':len(result['sources']), 'expectedCount':len(result['sources']), 'complete':True,
        'captured_at':captured, 'source_device':CONTAINER, 'capture_mode':'android_app_sqlite', 'status':'success',
        'native_conversation_id':result['conversation_id'], 'native_request_id':result['request_id'],
        'native_answer_id':result['answer_id'], 'batch_id':task['batch'], 'round':(task['ordinal']-1)//question_count+1,
        'question_index':(task['ordinal']-1)%question_count+1, 'body_capture_complete':True,
        'native_result':result}
    return {'request_id':identity, 'source_device':CONTAINER,'sent_at':captured,'payload':payload}


def main():
    STATE.mkdir(parents=True,exist_ok=True)
    for name in ('outbox','receipts'):(STATE/name).mkdir(exist_ok=True)
    queue=Queue(STATE/'tasks.sqlite')
    questions_path=Path(os.environ.get('DOUBAO_QUESTIONS_FILE',str(Path(__file__).parent/'geo_questions.json')))
    questions=json.loads(questions_path.read_text('utf-8-sig'))
    rounds=int(os.environ.get('DOUBAO_ROUNDS','5'))
    if not questions or len(set(questions))!=len(questions) or not all(isinstance(q,str) and q.strip() for q in questions):
        raise ValueError('Distinct non-empty questions required')
    if not 1<=rounds<=20:raise ValueError('Rounds must be 1-20')
    planned=len(questions)*rounds
    manifest={'batch':BATCH,'questions':questions,'rounds':rounds,'container':CONTAINER,'serial':SERIAL}
    manifest_path=STATE/'capture_manifest.json'
    if manifest_path.exists() and json.loads(manifest_path.read_text())!=manifest:
        raise ValueError('Existing batch settings cannot change')
    atomic_json(manifest_path,manifest)
    queue.enqueue(BATCH,questions*rounds,True)
    config=json.loads(RECEIVER.read_text('utf-8-sig'))
    url='http://127.0.0.1:'+str(config['port'])
    session=requests.Session()
    session.headers['Authorization']='Bearer '+config['token']
    session.get(url+'/api/v1/health',timeout=15).raise_for_status()
    worker_args=[sys.executable,str(Path(__file__).parent/'unattended_worker.py'),
        '--state-dir',str(STATE),'--container',CONTAINER,'--serial',SERIAL,'run','--once','--send-interval',os.environ.get('DOUBAO_SEND_INTERVAL','30'),
        '--answer-timeout',os.environ.get('DOUBAO_ANSWER_TIMEOUT','300')]
    if os.environ.get('DOUBAO_ISOLATE_TASK_ERRORS')=='1':worker_args.append('--continue-on-task-error')
    worker=subprocess.Popen(worker_args)
    signal.signal(signal.SIGTERM, stop_signal)
    try:
        while True:
            processed=0
            errors=[]
            rows=queue.db.execute("select * from tasks where state='completed' order by ordinal").fetchall()
            for row in rows:
                task=dict(row)
                done=queue.db.execute("select max(time) from events where task_id=? and event='completed'",(task['task_id'],)).fetchone()[0]
                item=envelope(task,done,len(questions))
                rid=item['request_id']
                receipt=STATE/'receipts'/(rid+'.json')
                if receipt.exists():
                    processed+=1
                    continue
                outbox=STATE/'outbox'/(rid+'.json')
                if not outbox.exists():atomic_json(outbox,item)
                try:
                    response=session.post(url+'/api/v1/captures',json=item,timeout=25)
                    response.raise_for_status()
                    result=session.get(url+'/api/v1/status/'+rid,timeout=25)
                    result.raise_for_status()
                    status=result.json()
                    if status.get('status')=='processed':
                        record=status['receipt']
                        if not record['analysis']['answer_present'] or record['analysis']['source_count']<1:
                            raise ValueError('Receiver receipt missing answer or sources')
                        atomic_json(receipt,record)
                        processed+=1
                    elif status.get('error'):errors.append({'task':task['ordinal'],'error':'receiver_analysis_pending'})
                except (requests.RequestException,ValueError,KeyError) as exc:
                    errors.append({'task':task['ordinal'],'error':type(exc).__name__})
            summary=queue.summary()
            health={'time':time.time(),'heartbeat_expires_at':time.time()+45,'bridge_pid':os.getpid(),
                'batch':BATCH,'planned':planned,'captured':len(rows),
                'geo_processed':processed,'tasks':summary,'worker_exit':worker.poll(),'delivery_errors':errors,
                'status':'complete' if processed==planned else ('running_with_errors' if summary.get('needs_attention') and worker.poll() is None else 'needs_attention' if summary.get('needs_attention') else 'running')}
            next_task=queue.next_task()
            if not summary.get('needs_attention') and next_task and next_task.get('not_before',0)>time.time():
                health.update(status='running_backoff',next_action_at=next_task['not_before'],capture_retry=next_task['capture_retries'])
            atomic_json(STATE/'bridge_health.json',health)
            if worker.poll()==0 and (STATE/'maintenance_pause.json').exists() and processed==len(rows):
                return 0
            if processed==planned:
                worker.wait(timeout=30)
                return 0
            if worker.poll() is not None and summary.get('needs_attention') and processed==len(rows):return 2
            if worker.poll() not in (None,0,2):return 1
            time.sleep(5)
    finally:
        if worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=20)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait(timeout=5)
        record_shutdown(STATE, worker.poll())


if __name__=='__main__':
    if sys.argv[1:] == ['--mark-stopped']:
        record_shutdown(STATE,reason='systemd_stop:'+os.environ.get('SERVICE_RESULT','manual'))
    else:
        raise SystemExit(main())

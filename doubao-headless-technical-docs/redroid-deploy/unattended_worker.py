"""Linux-local supervised worker. It fails visibly rather than guessing or resending."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sqlite3
import socket
import signal
import re
from contextlib import contextmanager
import time

from unattended_core import DataError, Queue, lookup

P = 'com.larus.nova:id/'

@contextmanager
def deadline(seconds):
    def expired(signum, frame):
        raise TimeoutError('Android operation exceeded its wall-clock deadline')
    previous=signal.signal(signal.SIGALRM,expired)
    signal.setitimer(signal.ITIMER_REAL,seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL,0)
        signal.signal(signal.SIGALRM,previous)

def notify(message):
    address=os.environ.get('NOTIFY_SOCKET')
    if not address:
        return
    if address.startswith('@'):
        address='\0'+address[1:]
    with socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM) as client:
        client.settimeout(1)
        client.connect(address)
        client.sendall(message.encode())

def atomic_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w',encoding='utf-8') as file:
        json.dump(value,file,ensure_ascii=False,indent=2)
        file.flush()
        os.fsync(file.fileno())
    os.replace(temporary,path)
    directory_fd=os.open(path.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)

def databases(container):
    info = json.loads(subprocess.check_output(['docker','inspect',container],timeout=10))[0]
    mount = next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data')
    directory = Path(mount)/'data/com.larus.nova/databases'
    result = []
    for path in directory.glob('im_database_*'):
        if path.name.endswith(('-wal','-shm','-journal')):
            continue
        with path.open('rb') as file:
            if file.read(16)==b'SQLite format 3\x00':
                result.append(path)
    if not result:
        raise DataError('No readable chat databases; login/schema must be checked')
    return result

class Android:
    def __init__(self, serial, adb):
        os.environ['ADBUTILS_ADB_PATH'] = adb
        subprocess.run([adb,'connect',serial],check=True,timeout=15,capture_output=True)
        import uiautomator2 as u2
        self.device = u2.connect(serial)

    def tap(self, selector):
        if not selector.exists:
            raise DataError('Required App control is missing')
        info = selector.info['bounds']
        self.device.shell(['input','tap',str((info['left']+info['right'])//2),str((info['top']+info['bottom'])//2)])
        time.sleep(.8)

    def ready(self):
        d = self.device
        if d.app_info('com.larus.nova').get('versionCode') != 15020040:
            raise DataError('Doubao APK changed; compatibility must be revalidated')
        d.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])
        create = d(resourceId=P+'larus_chat_top_left_create_new_cvs')
        # ARM translation needs a longer cold start after an emulator reboot.
        if not create.wait(timeout=35):
            d.shell(['am','force-stop','com.larus.nova'])
            d.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])
            if not create.wait(timeout=20):
                raise DataError('App did not become ready; login/native crash/UI must be checked')
        tts = d(description='朗读已打开')
        if tts.exists:
            self.tap(tts)
        self.tap(create)
        edit = d(resourceId=P+'input_text')
        if not edit.exists:
            self.tap(d(resourceId=P+'action_input'))
        if not edit.wait(timeout=5):
            raise DataError('Text input did not appear')

    def send(self, question, before_click=None):
        from uiautomator2.exceptions import UiObjectNotFoundError
        d = self.device
        edit = d(resourceId=P+'input_text')
        verified = False
        # The input can briefly disappear during the new-chat animation. Only
        # retry text entry; the send click is outside this retry block.
        for attempt in range(2):
            try:
                edit.set_text(question,timeout=5)
                if edit.get_text(timeout=3) == question:
                    verified = True
                    break
            except UiObjectNotFoundError:
                if attempt == 1:
                    raise
            time.sleep(.5)
        if not verified:
            raise DataError('Input text does not match this task; sending is forbidden')
        if before_click:
            before_click()
        self.tap(d(resourceId=P+'action_send'))

    def evidence(self, directory, task_id):
        # Evidence failures must not invalidate an already validated answer.
        try:
            with deadline(10):
                self.device.screenshot().save(directory/(task_id+'.png'))
                (directory/(task_id+'.xml')).write_text(self.device.dump_hierarchy(),encoding='utf-8')
        except Exception:
            pass

def export(queue, directory):
    import fcntl
    # CLI export and the daemon may run together. Serialize both the snapshot
    # and publication, otherwise an older snapshot can overwrite newer results.
    with (directory/'export.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        rows = []
        for question, result in queue.db.execute("select question,result_json from tasks where state='completed' order by rowid"):
            item = json.loads(result)
            item['question'] = question
            rows.append(item)
        atomic_json(directory/'answers.json',rows)
    return len(rows)

def run(args, queue, directory):
    import fcntl
    # A second state directory must not allow another worker to drive this App.
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', args.container):
        raise ValueError('Unsafe container name')
    device_lock = Path('/run/lock') / ('redroid-doubao-' + args.container + '.lock')
    device_handle = device_lock.open('a')
    os.chmod(device_lock, 0o600)
    fcntl.flock(device_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    lock = (directory/'worker.lock').open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    android = None
    last_export_count = -1
    notify('READY=1')
    while True:
        notify('WATCHDOG=1')
        task = queue.next_task()
        summary = queue.summary()
        status = 'needs_attention' if summary.get('needs_attention') else ('working' if task else 'idle')
        notify('STATUS=' + status + ' ' + json.dumps(summary, sort_keys=True))
        attention_ids=[r[0] for r in queue.db.execute("select task_id from tasks where state='needs_attention'")]
        atomic_json(directory/'health.json',{'time':time.time(),'status':status,'tasks':summary,
                    'task_id':task['task_id'] if task and status=='working' else None,'attention_task_ids':attention_ids})
        completed = summary.get('completed',0)
        if completed != last_export_count:
            export(queue,directory)
            last_export_count = completed
        if summary.get('needs_attention'):
            # Circuit breaker: do not keep relaunching a crashing App.
            return 2
        if task is None:
            if args.once:
                return 0
            time.sleep(10)
            continue
        try:
            paths = databases(args.container)
            observed = lookup(paths,task)
            finish_unsent = (task['state']=='prepared' and observed['status']=='absent'
                            and queue.may_finish_unsent(task['task_id']))
            if task['state']=='pending' or finish_unsent:
                if observed['status']!='absent':
                    raise DataError('Pending task already has an App request; inspect state before proceeding')
                if android is None:
                    with deadline(45):
                        android = Android(args.serial,args.adb)
                    notify('WATCHDOG=1')
                try:
                    with deadline(70):
                        android.ready()
                except Exception as exc:
                    queue.retry_preparation(task['task_id'],str(exc))
                    android.evidence(directory,task['task_id'])
                    if args.once and queue.summary().get('needs_attention'):
                        continue
                    time.sleep(args.retry_delay)
                    continue
                notify('WATCHDOG=1')
                if task['state']=='pending':
                    queue.prepare(task['task_id'], protocol='phase-v2')
                else:
                    with queue.db:
                        queue.event(task['task_id'], 'resume_before_first_click')
                # Intent is durable BEFORE the UI send. If anything fails here,
                # restart reconciles the same marker and NEVER sends it again.
                try:
                    with deadline(25):
                        android.send(task['wire_question'], lambda: queue.click_attempt(task['task_id']))
                except Exception as exc:
                    with queue.db:
                        queue.event(task['task_id'],'send_uncertain',str(exc))
                task = queue.next_task()
                observed = lookup(paths,task)
            if observed['status']=='complete':
                queue.complete(task['task_id'],observed)
                if android:
                    android.evidence(directory,task['task_id'])
                print('Completed:',task['task_id'],flush=True)
                continue
            if observed.get('request_id'):
                queue.attach_request(task['task_id'],observed['request_id'])
            if time.time()-task['prepared_at']>args.answer_timeout:
                queue.attention(task['task_id'],'Send/answer is unresolved; no automatic resend')
            else:
                time.sleep(args.poll_interval)
        except (DataError,sqlite3.DatabaseError) as exc:
            queue.attention(task['task_id'],str(exc))
        except Exception as exc:
            # Infrastructure faults leave prepared state intact for restart.
            with queue.db:
                queue.event(task['task_id'],'infrastructure_error',type(exc).__name__+': '+str(exc))
            atomic_json(directory/'health.json',{'time':time.time(),'status':'infrastructure_error','error':str(exc),'tasks':queue.summary()})
            raise

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--state-dir',type=Path,default=Path('/home/user/redroid-doubao/hpe14-acceptance'))
    parser.add_argument('--container',default='doubao-hpe14-13-test')
    parser.add_argument('--serial',default='127.0.0.1:5557')
    parser.add_argument('--adb',default='/home/user/redroid-doubao/linux-tools/platform-tools/adb')
    commands = parser.add_subparsers(dest='command',required=True)
    enqueue = commands.add_parser('enqueue')
    enqueue.add_argument('--batch',required=True)
    enqueue.add_argument('--questions',type=Path,required=True)
    enqueue.add_argument('--require-sources',action='store_true')
    commands.add_parser('status')
    commands.add_parser('export')
    audit = commands.add_parser('audit-existing')
    audit.add_argument('--questions',type=Path,required=True)
    worker = commands.add_parser('run')
    worker.add_argument('--once',action='store_true')
    worker.add_argument('--answer-timeout',type=int,default=300)
    worker.add_argument('--poll-interval',type=float,default=5)
    worker.add_argument('--retry-delay',type=float,default=20)
    args = parser.parse_args()
    args.state_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(args.state_dir,0o700)
    queue = Queue(args.state_dir/'tasks.sqlite')
    os.chmod(queue.path,0o600)
    if args.command=='enqueue':
        queue.enqueue(args.batch,json.loads(args.questions.read_text(encoding='utf-8-sig')),args.require_sources)
        print(json.dumps(queue.summary()))
    elif args.command=='status':
        print(json.dumps(queue.summary()))
        for row in queue.db.execute("select task_id,state,attempts,error from tasks where state!='completed'"):
            print(json.dumps(dict(row),ensure_ascii=False))
    elif args.command=='export':
        print('Exported:',export(queue,args.state_dir))
    elif args.command=='audit-existing':
        results=[]
        for i,q in enumerate(json.loads(args.questions.read_text(encoding='utf-8-sig')),1):
            row=lookup(databases(args.container),{'task_id':'audit-'+str(i),'wire_question':q})
            results.append(row)
            print(json.dumps({'index':i,'status':row['status'],'sources':len(row.get('sources',[])),'citations':len(row.get('citations',[]))}))
        atomic_json(args.state_dir/'audit-existing.json',results)
    else:
        return run(args,queue,args.state_dir)
    return 0

if __name__=='__main__':
    raise SystemExit(main())

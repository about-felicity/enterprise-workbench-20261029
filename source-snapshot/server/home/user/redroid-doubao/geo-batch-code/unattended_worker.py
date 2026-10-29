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
import xml.etree.ElementTree as ET
from contextlib import contextmanager
import time

from unattended_core import DataError, Queue, lookup, is_transient_error

P = 'com.larus.nova:id/'

def assert_fresh_chat(hierarchy):
    """An input box also exists in a failed old chat; it is not readiness proof."""
    for node in ET.fromstring(hierarchy).iter('node'):
        if node.get('resource-id') == P+'input_text':
            continue
        if '采集任务编号：' in node.get('text', ''):
            raise DataError('新对话创建未成功：仍显示上一题的采集消息，已阻止继续发送')

def is_blank_landing(hierarchy):
    nodes=list(ET.fromstring(hierarchy).iter('node'))
    return (any(n.get('text')=='为你推荐' for n in nodes)
            and any(n.get('resource-id')==P+'input_text' for n in nodes)
            and any(n.get('resource-id')==P+'back_icon' and n.get('content-desc')=='返回' for n in nodes)
            and not any('采集任务编号：' in n.get('text','') for n in nodes))

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

    def wait_for_chat(self, create, timeout):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            message = self.device(resourceId='com.android.permissioncontroller:id/permission_message')
            if message.exists:
                text = message.get_text()
                # Only dismiss this observed optional notification prompt.
                # Login/verification and other permissions require attention.
                if '豆包' in text and ('notifications' in text.lower() or '通知' in text):
                    if self.dismiss_notification_prompt():
                        continue
            if create.exists:
                return True
            if is_blank_landing(self.device.dump_hierarchy()):
                return True
            time.sleep(.5)
        return False

    def dismiss_notification_prompt(self):
        message=self.device(resourceId='com.android.permissioncontroller:id/permission_message')
        if not message.exists:return False
        text=message.get_text()
        if '豆包' not in text or not ('notifications' in text.lower() or '通知' in text):return False
        for name in ('permission_deny_button','permission_deny_and_dont_ask_again_button'):
            button=self.device(resourceId='com.android.permissioncontroller:id/'+name)
            if button.exists:
                self.tap(button)
                return True
        return False

    def ready(self):
        d = self.device
        if d.app_info('com.larus.nova').get('versionCode') != 15020040:
            raise DataError('Doubao APK changed; compatibility must be revalidated')
        d.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])
        create = d(resourceId=P+'larus_chat_top_left_create_new_cvs')
        # ARM translation needs a longer cold start after an emulator reboot.
        if not self.wait_for_chat(create,35):
            d.shell(['am','force-stop','com.larus.nova'])
            d.shell(['am','start','-W','-n','com.larus.nova/com.larus.home.impl.alias.AliasActivity1'])
            if not self.wait_for_chat(create,20):
                raise DataError('App did not become ready; login/native crash/UI must be checked')
        tts = d(description='朗读已打开')
        if tts.exists:
            self.tap(tts)
        if create.exists:
            self.tap(create)
        elif not is_blank_landing(d.dump_hierarchy()):
            raise DataError('New-chat control missing and empty landing page not verified')
        edit = d(resourceId=P+'input_text')
        if not edit.exists:
            self.tap(d(resourceId=P+'action_input'))
        if not edit.wait(timeout=5):
            raise DataError('Text input did not appear')
        # Account2 reproduced a transient empty screen followed by the old
        # failed chat. Check across the transition, not only at first paint.
        for _ in range(3):
            time.sleep(1)
            assert_fresh_chat(d.dump_hierarchy())

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
        assert_fresh_chat(d.dump_hierarchy())
        button=d(resourceId=P+'action_send')
        if not button.wait(timeout=5):
            raise DataError('Send button did not become ready; no click dispatched')
        # Keyboard/layout transitions can move the target after text entry.
        stable=False
        for _ in range(6):
            first=button.info
            time.sleep(.4)
            second=button.info
            if first['bounds']==second['bounds'] and second.get('enabled',True):
                stable=True
                break
        if not stable or edit.get_text(timeout=3)!=question:
            raise DataError('Send target/input did not stabilize; no click dispatched')
        assert_fresh_chat(d.dump_hierarchy())
        if before_click:
            before_click()
        self.tap(button)

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
    with device_lock.open('a') as device_handle, (directory/'worker.lock').open('a') as lock:
        os.chmod(device_lock, 0o600)
        fcntl.flock(device_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        return run_locked(args,queue,directory)


def run_locked(args,queue,directory):
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
        if (directory/'maintenance_pause.json').exists() and (task is None or task['state']=='pending'):
            atomic_json(directory/'health.json',{'time':time.time(),'status':'maintenance_paused','tasks':summary})
            return 0
        if summary.get('needs_attention') and not getattr(args,'continue_on_task_error',False):
            # Circuit breaker: do not keep relaunching a crashing App.
            return 2
        if task is None:
            if args.once:
                return 0
            time.sleep(10)
            continue
        if task['state']=='pending' and task.get('not_before',0)>time.time():
            atomic_json(directory/'health.json',{'time':time.time(),'status':'backoff','task_id':task['task_id'],'next_action_at':task['not_before'],'tasks':summary})
            time.sleep(min(task['not_before']-time.time(),5))
            continue
        try:
            paths = databases(args.container)
            observed = lookup(paths,task)
            finish_unsent = (task['state']=='prepared' and observed['status']=='absent'
                            and queue.may_finish_unsent(task['task_id']))
            if task['state']=='pending' or finish_unsent:
                last_click = queue.db.execute("select max(time) from events where event='send_click_intent_committed'").fetchone()[0]
                remaining = (last_click or 0) + getattr(args, 'send_interval', 0) - time.time()
                if remaining > 0:
                    time.sleep(min(remaining, 5))
                    continue
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
                    if queue.may_finish_unsent(task['task_id']):
                        queue.retry_preparation(task['task_id'],str(exc))
                        android.evidence(directory,task['task_id'])
                        time.sleep(args.retry_delay)
                        continue
                else:
                    with queue.db:queue.event(task['task_id'],'send_tap_returned','ADB tap returned; native request still requires reconciliation')
                task = queue.next_task()
                observed = lookup(paths,task)
            if observed['status']=='complete':
                if is_transient_error(observed):
                    delay=queue.schedule_transient_retry(task['task_id'],observed)
                    if android:android.evidence(directory,task['task_id']+'-transient-'+str(task.get('capture_retries',0)))
                    print('Confirmed transient error; retry after',delay,'seconds:',task['task_id'],flush=True)
                    continue
                queue.complete(task['task_id'],observed)
                if android:
                    android.evidence(directory,task['task_id'])
                print('Completed:',task['task_id'],flush=True)
                continue
            if observed.get('request_id'):
                queue.attach_request(task['task_id'],observed['request_id'])
                if observed.get('native_request_confirmed') and not queue.db.execute("select 1 from events where task_id=? and event='native_request_confirmed' and id>?",(task['task_id'],queue.attempt_boundary(task['task_id']))).fetchone():
                    with queue.db:queue.event(task['task_id'],'native_request_confirmed',observed['request_id'])
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
    worker.add_argument('--send-interval',type=float,default=0)
    worker.add_argument('--continue-on-task-error',action='store_true')
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

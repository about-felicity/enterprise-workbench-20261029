"""Recover only two proven-unsent first tasks after fixing notification denial."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time

PANEL=Path('/opt/monitor/geo-capture')
CODE=Path('/home/user/redroid-doubao/geo-batch-code')
ROOT=PANEL/'soak/all-channel-soak2h-1792056244'
JOBS={'doubao1':('geo-panel-doubao1-20261015-172454-e5bec1f9','doubao-hpe14-13-test',5557),
      'doubao2':('geo-panel-doubao2-20261015-172455-301bb730','doubao-hpe14-account2',5558)}
path=CODE/'unattended_worker.py'
current_hash=hashlib.sha256(path.read_bytes()).hexdigest()
release_hash=hashlib.sha256(Path('/tmp/doubao_worker_notification_fix.py').read_bytes()).hexdigest()
assert current_hash in {'3a1af06cbc2074bb7acdb52ef9c6d9fe7ef8da26dc4d5175d404a18571c31831',release_hash}
backup=ROOT/'diagnostics/notification-denial-recovery'
backup.mkdir(parents=True,mode=0o700,exist_ok=True)
if not (backup/'unattended_worker.before.py').exists():shutil.copy2(path,backup/'unattended_worker.before.py')
shutil.copy2('/tmp/doubao_worker_notification_fix.py',path)
sys.path.insert(0,str(CODE));sys.path.insert(0,str(PANEL))
from unattended_worker import Android,databases
from unattended_core import lookup
from native_soak import API,operation
api=API();results=[]
for model,(batch,container,port) in JOBS.items():
    service='geo-native@'+batch+'.service'
    assert subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip() not in {'active','activating','deactivating'}
    root=Path('/home/user/redroid-doubao/batches')/batch
    with closing(sqlite3.connect(root/'tasks.sqlite')) as db:
        db.row_factory=sqlite3.Row
        if not (backup/(model+'-tasks.before.sqlite')).exists():
            with closing(sqlite3.connect(backup/(model+'-tasks.before.sqlite'))) as copy:db.backup(copy)
        tasks=db.execute("select * from tasks where state!='pending'").fetchall()
        assert len(tasks)==1
        task=dict(tasks[0]);assert task['ordinal']==1 and task['state']=='needs_attention'
        assert task['prepared_at'] is None and not task['request_id'] and not task['answer_id'] and not task['result_json']
        assert task['error']=='Required App control is missing'
        assert db.execute("select count(*) from events where event in ('send_intent_committed','send_click_intent_committed','send_uncertain')").fetchone()[0]==0
        assert lookup(databases(container),task)['status']=='absent'
        android=Android('127.0.0.1:'+str(port),'/home/user/redroid-doubao/linux-tools/platform-tools/adb')
        android.ready()  # Normal new-chat setup only; no send call.
        assert lookup(databases(container),task)['status']=='absent'
        with db:
            db.execute("update tasks set state='pending',attempts=0,error=null where task_id=? and state='needs_attention'",(task['task_id'],))
            db.execute('insert into events(task_id,time,event,detail) values(?,?,?,?)',(
                task['task_id'],time.time(),'operator_notification_preflight_recovery',
                'Notification denial second variant fixed; zero send intents/clicks; original task absent in native DB; first task only'))
    operation(ROOT,api,model+'-notification-recovery-resume',model,'resume',{})
    results.append({'model':model,'batch':batch,'task_ordinal':1,'unsent_native_absence_verified':True,
                    'previous_failure_evidence_retained':True,'resumed_at':time.time()})
record={'cause':'Repeated Android optional notification permission dialog uses permission_deny_and_dont_ask_again_button; old worker assumed permission_deny_button',
        'backup':str(backup),'recovered':results,'app_data_cleared':False,'unknown_send_retried':False}
(ROOT/'notification_preflight_recovery.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))

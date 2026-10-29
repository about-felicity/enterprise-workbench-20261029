import os,sys,json,time,fcntl
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao')
from unattended_core import Queue
root=Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015')
lock=Path('/run/lock/redroid-yuanbao-yuanbao-hpe14-android13.lock').open('a')
fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
q=Queue(root/'tasks.sqlite');task=q.next_task()
if task['ordinal']!=1 or task['state']!='prepared' or not q.may_finish_unsent(task['task_id']):raise RuntimeError('Click is not safely repeatable')
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
edit=d(className='android.widget.EditText');button=d(className='android.widget.Button',clickable=True)
if edit.count!=1 or edit.get_text()!=task['wire_question'] or button.count!=1:raise RuntimeError('Input/send control mismatch')
first=button.info['bounds'];time.sleep(.5);last=button.info
if first!=last['bounds'] or not last['enabled']:raise RuntimeError('Unstable send control')
q.click_attempt(task['task_id'])
d.shell(['input','tap',str((first['left']+first['right'])//2),str((first['top']+first['bottom'])//2)])
with q.db:q.event(task['task_id'],'send_tap_returned')
print(json.dumps({'ordinal':1,'send_clicks_committed':1,'result_reconciliation_required':True}))

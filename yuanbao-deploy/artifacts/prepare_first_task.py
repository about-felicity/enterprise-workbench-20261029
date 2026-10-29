import os,sys,json,time
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao')
from unattended_core import Queue
from unattended_worker import atomic_json
BASE=Path('/home/user/redroid-yuanbao')
root=BASE/'batches/geo-yuanbao-21x5-20261015'
root.mkdir(parents=True,exist_ok=True,mode=0o700)
questions=json.loads(Path('/home/user/redroid-doubao/geo-batch-code/geo_questions.json').read_text('utf8'))
manifest={'model':'yuanbao','batch':root.name,'questions':questions,'rounds':5,'interval':45,'container':'yuanbao-hpe14-android13','serial':'127.0.0.1:5559'}
mp=root/'capture_manifest.json'
if mp.exists() and json.loads(mp.read_text())!=manifest:raise RuntimeError('Existing manifest differs')
atomic_json(mp,manifest)
q=Queue(root/'tasks.sqlite');q.enqueue(root.name,questions*5,True)
task=q.next_task()
if task['ordinal']!=1 or (task['state']=='prepared' and not q.may_finish_unsent(task['task_id'])):raise RuntimeError('No safe first unsent task')
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5559')
if d(text='快速作答，处理日常问题').exists:d.press('back')
if task['state']=='pending':q.prepare(task['task_id'],protocol='phase-v2')
edit=d(className='android.widget.EditText')
if edit.count!=1:raise RuntimeError('Exactly one editor required')
edit.set_text(task['wire_question'])
if edit.get_text()!=task['wire_question']:raise RuntimeError('Editor mismatch; no send')
print(json.dumps({'prepared_ordinal':task['ordinal'],'input_verified':True,'send_click_attempted':False,'queue':q.summary()}))

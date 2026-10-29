import sqlite3,json,time,os,xml.etree.ElementTree as E
from unattended_core import lookup
from unattended_worker import databases
p='/home/user/redroid-doubao/hpe14-acceptance/tasks.sqlite';db=sqlite3.connect(p);db.row_factory=sqlite3.Row
t=db.execute("select * from tasks where state='prepared' limit 1").fetchone()
if t:
 t=dict(t);print(json.dumps({k:t[k] for k in ['task_id','state','prepared_at','request_id','attempts','error']}));print('age',time.time()-t['prepared_at'])
 print('events', [dict(r) for r in db.execute('select event,detail,time from events where task_id=?',(t['task_id'],))])
 r=lookup(databases('doubao-hpe14-13-test'),t);print('observation',r.get('status'),r.get('request_id'),r.get('finished'))
 os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
 import uiautomator2 as u2
 d=u2.connect('127.0.0.1:5557');xml=d.dump_hierarchy();nodes=list(E.fromstring(xml).iter('node'))
 print('UI',[(n.get('resource-id'),len(n.get('text','')),n.get('text')==t['wire_question']) for n in nodes if any(z in n.get('resource-id','') for z in ['input_text','action_send','create_new_cvs'])])
 print('current',d.app_current())

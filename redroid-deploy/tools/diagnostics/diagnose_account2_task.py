
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,json,os,subprocess
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue,lookup
from unattended_worker import databases
q=Queue('/home/user/redroid-doubao/batches/geo-products-21x5-account2-20261013/tasks.sqlite')
t=q.next_task()
if t:
    print(json.dumps({k:t[k] for k in ('task_id','state','prepared_at','request_id')},ensure_ascii=False))
    print([dict(r) for r in q.db.execute('select event,detail,time from events where task_id=?',(t['task_id'],))])
    result=lookup(databases('doubao-hpe14-account2'),t)
    print(json.dumps({k:v for k,v in result.items() if k in ('status','request_id','answer_id','finished')},ensure_ascii=False))
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5558')
import xml.etree.ElementTree as ET
tree=ET.fromstring(d.dump_hierarchy())
print(json.dumps([{'id':e.get('resource-id'),'text':e.get('text'),'desc':e.get('content-desc')} for e in tree.iter('node') if e.get('text') or e.get('content-desc')],ensure_ascii=False))

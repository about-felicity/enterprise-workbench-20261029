
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys, json
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_core import Queue, lookup
from unattended_worker import databases
batch='geo-products-21x5-20261013'
q=Queue('/home/user/redroid-doubao/batches/'+batch+'/tasks.sqlite')
for row in q.db.execute("select * from tasks where state='needs_attention'"):
    task=dict(row)
    print(json.dumps({k:v for k,v in task.items() if k not in ('result','wire_question')},ensure_ascii=False))
    print(json.dumps([dict(r) for r in q.db.execute('select event,detail,time from events where task_id=? order by time desc limit 6',(task['task_id'],))],ensure_ascii=False))
    try:
        result=lookup(databases('doubao-hpe14-13-test'),task)
        print(json.dumps({k:v for k,v in result.items() if k in ('status','request_id','answer_id','finished')},ensure_ascii=False))
    except Exception as exc:
        print(type(exc).__name__,str(exc))
import os, xml.etree.ElementTree as ET
os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
import uiautomator2 as u2
d=u2.connect('127.0.0.1:5557')
print('foreground',d.app_current())
tree=ET.fromstring(d.dump_hierarchy())
print(json.dumps([{'id':e.get('resource-id'),'text':e.get('text'),'desc':e.get('content-desc')} for e in tree.iter('node') if e.get('text') or e.get('content-desc')],ensure_ascii=False))

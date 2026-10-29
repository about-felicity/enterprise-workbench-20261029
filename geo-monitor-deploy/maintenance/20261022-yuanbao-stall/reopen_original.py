"""One-time read-only reopening of the observed history row, not answer retry."""
import sys,time,json,xml.etree.ElementTree as ET
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from android_ui import Android
from question_only_adapters import yuanbao_reader
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261022-090005-705819fb')
import sqlite3
db=sqlite3.connect(root.joinpath('tasks.sqlite'));db.row_factory=sqlite3.Row
task=dict(db.execute("select * from tasks where task_id='ec2d8635-f417-59c4-ab60-b6b5db6a9193'").fetchone())
binding=json.loads((root/(task['task_id']+'.binding.json')).read_text())
assert binding['conversation_id']=='0RRIw2HvYau' and task['state']=='prepared'
a=Android();d=a.device
for title in ('沐浴精油推荐对比','眉毛增长液成分与功效说明'):
 entry=d(description='抽屉页入口');assert entry.count==1;a.tap(entry);time.sleep(1)
 item=d(text=title);assert item.count==1;a.tap(item);time.sleep(2)
r=yuanbao_reader(root)
try:
 result=r.lookup(task)
 print(json.dumps({k:result.get(k) for k in ('status','reason','phase','request_id','conversation_id','answer_id')},ensure_ascii=False))
 print('chars',len(result.get('body_markdown','')),'sources',len(result.get('sources',[])))
finally:r.close()
D=Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall')
(D/'after-reopen-ui.xml').write_text(d.dump_hierarchy())
print(json.dumps([n.get('text') for n in ET.fromstring(d.dump_hierarchy()).iter('node') if n.get('text')],ensure_ascii=False)[:1500])

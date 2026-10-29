import sys,json,sqlite3
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_core import message_text
from unattended_worker import databases
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao2-20261019-090003-88e4f45b');snap=json.loads((root/'1188d66f-eb41-529f-89a6-5d34ea3e6a3c-attempt-0.pre-send.json').read_text())
for item in snap['databases']:
 with sqlite3.connect(Path(item['database']).as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  rows=db.execute('select rowid,* from im_message where rowid>? order by rowid',(item['max_rowid'],)).fetchall()
  print('new_rows',len(rows))
  for r in rows[-6:]:
   print(json.dumps({**{k:r[k] for k in ['rowid','user_type','message_id','server_index','conversation_id']},'is_expected_question':message_text(r)=='推荐一款防脱精华液','text_length':len(message_text(r))},ensure_ascii=False))
import uiautomator2 as u2
s=u2.connect('127.0.0.1:5558');xml=s.dump_hierarchy()
import xml.etree.ElementTree as E
print('visible_text',json.dumps([e.attrib['text'] for e in E.fromstring(xml).iter('node') if e.attrib.get('text')][:25],ensure_ascii=False))

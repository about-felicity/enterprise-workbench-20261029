"""Private creation persistence cannot construct the GEO receiver."""
import json,sqlite3,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from delivery import Delivery

class PrivateTests(unittest.TestCase):
 def test_retired_web_entry_cannot_send_or_touch_its_journal(self):
  from capture_bridge import run
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);config=root/'config.json';config.write_text('{"model":"deepseek"}')
   (root/'deepseek_backend.json').write_text('{"backend":"android"}')
   with patch('capture_bridge.Delivery',side_effect=AssertionError('Legacy web delivery must not start')):
    self.assertEqual(run(config,root,root),0)
   self.assertFalse((root/'batches').exists())
 def test_private_commit_is_idempotent_and_never_opens_geo_receiver(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
   db.executescript('create table tasks(task_id text,state text,ordinal int,question text,result_json text,batch text);create table events(task_id text,event text,time real);')
   value={'body_markdown':'完整原文','sources':[{'title':'原始资料','url':'https://example.com/a'}],'conversation_id':'conversation-one','body_capture_complete':True,'source_capture_complete':True,'capture_mode':'android_app_wcdb_question_only'}
   db.execute('insert into tasks values(?,?,?,?,?,?)',('task-one','completed',1,'专用问题',json.dumps(value),'private-batch'))
   db.execute('insert into events values(?,?,?)',('task-one','completed',1792200000));db.commit()
   with patch('delivery.ReceiverDelivery',side_effect=AssertionError('GEO receiver must never open')):
    delivery=Delivery(root/'native',{'private_root':str(root),'questions':['专用问题'],'rounds':1})
    first=delivery.sync(SimpleNamespace(db=db));second=delivery.sync(SimpleNamespace(db=db))
   self.assertEqual(first,second);self.assertEqual(first['captured'],1)
   self.assertEqual(len((root/'results.jsonl').read_text().splitlines()),1)
   with sqlite3.connect(root/'collector/tasks.sqlite') as store:self.assertEqual(store.execute('select count(*) from captures').fetchone()[0],1)
   self.assertFalse((root/'native/outbox').exists())
   self.assertFalse((root/'native/receipts').exists())

if __name__=='__main__':unittest.main()

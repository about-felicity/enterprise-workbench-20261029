"""Frozen native DeepSeek observations to the established model receiver, or private store."""
from contextlib import closing
from datetime import datetime,timezone
import json,sqlite3,sys
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
sys.path.append('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages')
from capture_bridge import Delivery as ReceiverDelivery
from geo_source_cards.runtime import atomic_json,atomic_write

def result(task,completed):
 value=json.loads(task['result_json'])
 return {**value,'model':'deepseek','question':task['question'],'body':value['body_markdown'],
  'captured_at':datetime.fromtimestamp(completed,timezone.utc).isoformat(),
  'expected_source_count':len(value['sources']),'source_entries':value['sources'],
  'url':'deepseek-app://chat/'+value['conversation_id']}

class Delivery:
 def __init__(self,root,config):
  self.root=Path(root);self.config=config
  self.bridge=None if config.get('private_root') else ReceiverDelivery(self.root,{**config,'device':'deepseek-hpe14-android13','capture_label':'DeepSeek 安卓App'},Path('/opt/monitor'))
 def sync(self,queue):
  rows=[]
  for row in queue.db.execute("select * from tasks where state='completed' order by ordinal"):
   task=dict(row);completed=queue.db.execute("select max(time) from events where task_id=? and event='completed'",(task['task_id'],)).fetchone()[0]
   ordinal=(task['ordinal']-1)%len(self.config['questions']);round_=(task['ordinal']-1)//len(self.config['questions'])+1
   rows.append({'state':'completed','ordinal':ordinal,'round':round_,'task_id':task['task_id'],'batch':task['batch'],'finished':completed,'result':json.dumps(result(task,completed),ensure_ascii=False)})
  if self.bridge:
   metrics=self.bridge.sync(rows)
   return {'captured':metrics['captured'],'geo_processed':metrics['processed'],'delivery_errors':metrics['errors']}
  # Private creation material never constructs a receiver or reads its credential.
  private=Path(self.config['private_root']);collector=private/'collector';collector.mkdir(parents=True,exist_ok=True,mode=0o700)
  with closing(sqlite3.connect(collector/'tasks.sqlite')) as db:
   db.execute('create table if not exists captures(task_id text primary key,state text,result text)')
   for task in queue.db.execute('select task_id,state from tasks'):
    state='capturing' if task['state'] in {'prepared','needs_attention'} else task['state']
    db.execute('insert or ignore into captures values(?,?,null)',(task['task_id'],state))
    if state!='completed':db.execute('update captures set state=? where task_id=?',(state,task['task_id']))
   for row in rows:db.execute('insert or replace into captures values(?,?,?)',(row['task_id'],'completed',row['result']))
   db.commit()
  atomic_write(private/'results.jsonl',''.join(r['result']+'\n' for r in rows))
  return {'captured':len(rows),'geo_processed':len(rows),'delivery_errors':[]}

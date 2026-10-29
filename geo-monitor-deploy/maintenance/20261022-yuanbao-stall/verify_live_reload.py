"""Replay the saved interrupted observation through real read-only UI recovery.

Does not alter App model state, task state or send controls. The original answer
is already complete; this verifies navigation, not a newly induced interruption.
"""
import json,sqlite3,sys,shutil,time
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from history_refresh import refresh_original,memory_history
from question_only_adapters import yuanbao_reader
from android_ui import Android
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261022-090005-705819fb')
D=Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall');fixture=D/'live-replay-final';fixture.mkdir(exist_ok=True)
db=sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
t=dict(db.execute('select * from tasks where ordinal=6').fetchone())
assert t['state']=='prepared' and t['capture_retries']==0
binding=json.loads((root/(t['task_id']+'.binding.json')).read_text())
raw=json.loads((D/'before-native.json').read_text())
assert raw['content']['traceId']==t['request_id']
(fixture/(t['task_id']+'.native.json')).write_text(json.dumps(raw))
(fixture/(t['task_id']+'.binding.json')).write_text(json.dumps(binding))
reader=yuanbao_reader(root);a=Android();events=[]
import xml.etree.ElementTree as ET
for _ in range(8):
 if any(n.get('text')==t['wire_question'] for n in ET.fromstring(a.device.dump_hierarchy()).iter('node')):break
 a.device.shell(['input','swipe','360','350','360','850','400']);time.sleep(.5)
try:
 entries=reader.history_entries();proof=memory_history(binding,t,raw,entries)
 assert proof and proof['conversation_id']==binding['conversation_id']
 recovery=refresh_original(fixture,t,{'reason':'native_answer_interrupted'},a,reader.close,
     lambda *v:events.append(v),history_entries=reader.history_entries)
 assert recovery and recovery['phase']=='reloading_original_history',recovery
 result=reader.lookup(t)
 assert result['status']=='complete' and result['request_id']==t['request_id']
 assert result['conversation_id']==binding['conversation_id'] and result['answer_id']==binding['server_answer_id']
 clicks=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(t['task_id'],)).fetchone()[0]
 assert clicks==1
 output={'at':time.time(),'live_navigation':recovery,'memory_title_proof':proof['proof_source'],
  'request_id':result['request_id'],'conversation_id':result['conversation_id'],
  'body_length':len(result['body_markdown']),'sources':len(result['sources']),'original_clicks':clicks,'events':events,
  'scope':'saved interrupted observation replay; no new fault induced; original request only'}
 (D/'live-reload-verification.json').write_text(json.dumps(output,ensure_ascii=False,indent=2));print(json.dumps(output,ensure_ascii=False))
finally:reader.close()

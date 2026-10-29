"""Stop new isolated paid requests after repeated transport failures; drain current."""
import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
R=runtime.BASE/'quality-repair/20261021-consumer-voice';held=[]
for item in runtime.read(R/'inventory.json')['articles']:
 entry=R/item['key'];state=runtime.read(entry/'status.json')
 if state.get('reason')!='consumer_contract_maintenance':continue
 attempt=state.get('attempt',1)+1;side=entry/f'attempt-{attempt}'
 # No intent or API reservation may be discarded or interrupted.
 assert not any(side.rglob('api_state.json'))
 side.mkdir(parents=True,exist_ok=True)
 runtime.atomic_json(side/'control.json',{'paused':True,'reason':'consumer_contract_maintenance','message':'API transport failures: hold only unsent quality revisions; existing calls drain without replay','paused_epoch':time.time(),'revision':1})
 held.append({'key':item['key'],'attempt':attempt})
runtime.atomic_json(R/'transport-hold.json',{'at':time.time(),'held':held,'original_task_controls_unchanged':True,'active_calls_interrupted':0})
print(json.dumps({'held_unsent':len(held),'paid_requests_interrupted':0}))

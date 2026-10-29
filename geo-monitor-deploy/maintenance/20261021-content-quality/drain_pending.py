"""Hold not-yet-sent isolated repairs, letting current paid requests finish."""
import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
R=runtime.BASE/'quality-repair/20261021-consumer-voice';items=runtime.read(R/'inventory.json')['articles'];held=[]
for item in items:
 entry=R/item['key'];state=runtime.read(entry/'status.json')
 if state:continue
 side=entry/'attempt-1';side.mkdir(parents=True,exist_ok=True)
 runtime.atomic_json(side/'control.json',{'paused':True,'reason':'consumer_contract_maintenance','message':'尚未发送的质量修订等待合同更新，当前已发送请求不终止','paused_epoch':time.time(),'revision':1})
 held.append(item['key'])
runtime.atomic_json(R/'maintenance-hold.json',{'at':time.time(),'pending_held':held,'paid_calls_interrupted':0,'source_task_controls_unchanged':True})
print(json.dumps({'not_yet_sent_repairs_held':len(held),'paid_requests_not_interrupted':True}))

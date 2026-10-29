"""Drain active isolated repair; hold only selected articles not sent yet."""
import sys,time,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
R=runtime.BASE/'quality-repair/20261021-consumer-voice'
report=runtime.read(R/'followup-paused-20261021.json');held=[]
for item in report.get('selected',[]):
 entry=R/item['key'];state=runtime.read(entry/'status.json')
 if state.get('reason')!='consumer_contract_maintenance':continue
 attempt=state.get('attempt',1)+1;side=entry/f'attempt-{attempt}'
 if any(side.glob('calls/*/api_state.json')) or any(side.glob('calls/*/request.json')):continue
 runtime.atomic_json(side/'control.json',{'paused':True,'reason':'legacy_identity_preflight','message':'旧研究尚未绑定冻结产品身份，付款前维护暂停；原生产任务不变','paused_epoch':time.time(),'revision':1})
 held.append({'key':item['key'],'attempt':attempt})
runtime.atomic_json(R/'identity-preflight-hold.json',{'at':time.time(),'held':held,'original_task_controls_unchanged':True,'active_requests_interrupted':0})
print(json.dumps({'held_unsent':len(held),'active_requests_interrupted':0}))

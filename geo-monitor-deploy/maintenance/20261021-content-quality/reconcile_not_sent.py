"""Reconcile only a proven pre-send budget rejection; never clear unknown delivery."""
import hashlib,json,shutil,sqlite3,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1792479954-8a96bc88');active=runtime.read(root/'api/active.json')
assert runtime.read(root/'geo_worker.json').get('error')=='budget_exceeded'
assert runtime.read(root/'control.json').get('reason')=='consumer_prompt_maintenance'
assert active['state']=='REQUESTING'
run=root/'api/runs'/active['run_id'];call=run/'call'
for name in ['request.json','api_state.json','response.json']:assert not (call/name).exists(),name
identity=hashlib.sha256(str(call.resolve()).encode()).hexdigest()
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 assert db.execute('select count(*) from costs where id=?',(identity,)).fetchone()[0]==0
backup=root/'repair_evidence/consumer-budget-not-sent';assert not backup.exists();backup.mkdir(parents=True)
shutil.copy2(root/'api/active.json',backup/'active.json');ticket=root/'queue'/active['ticket']/'ticket.json';shutil.copy2(ticket,backup/'ticket.json')
t=runtime.read(ticket);runtime.atomic_json(ticket,{**t,'state':'needs_attention','error':'预算保护在发送前拒绝请求，未产生发送意图或费用预留；保留原稿待修订，不提高预算','pre_send_budget_rejected':True})
runtime.atomic_json(root/'api/active.json',{**active,'state':'SUBMITTED','pre_send_budget_rejected':True})
runtime.atomic_json(backup/'proof.json',{'at':time.time(),'request_file_absent':True,'send_intent_absent':True,'reservation_absent':True,'original_execution_preserved':True})
print('Pre-send rejection reconciled; task remains paused and budget unchanged')

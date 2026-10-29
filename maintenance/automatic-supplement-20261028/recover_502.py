import sys,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.daily_editorial import publish_ticket
root=runtime.BASE/'runs/creation-1793152105-2194b154';D=Path('/opt/monitor/maintenance/automatic-supplement-20261028');D.mkdir(parents=True,exist_ok=True)
with process_lock(root/'api/worker.lock',blocking=False),process_lock(root/'coordinator.lock',blocking=False):
 a=runtime.read(root/'api/active.json');p=root/'queue'/a['ticket']/'ticket.json';t=runtime.read(p)
 run=root/'api/runs'/a['run_id'];s=runtime.read(run/'skeleton-call/api_state.json')
 assert a['run_id']=='76ef69a505a649c836575086' and s['state']=='HTTP_REJECTED' and s['http_status']==502
 assert not list(run.rglob('response.json'))
 b=D/'502-recovery';b.mkdir(exist_ok=False)
 for f in [p,root/'api/active.json',root/'control.json']:shutil.copy2(f,b/f.name)
 replacement=publish_ticket(root,t['stage'],root/t['location'],list(t['inputs']),t['outputs'],{**t['meta'],'revision':t['meta'].get('revision',0)+1,'replaces':t['id'],'operator_502_recovery':True})
 atomic_json(p,{**t,'state':'revision_requested','replaced_by':replacement,'error':'HTTP 502，无可用答复；保留原请求及费用预留，用户要求恢复后创建独立补做执行'})
 atomic_json(root/'api/active.json',{**a,'state':'SUBMITTED'})
 atomic_json(b/'record.json',{'at':time.time(),'replacement':replacement,'original_cost_reservation_preserved':s['reservation'],'original_delivery_uncertain':True,'authorization':'REDACTED_CONFIGURE_LOCALLY'})
runtime.resume(root,check_balance=True)
print('replacement',replacement)

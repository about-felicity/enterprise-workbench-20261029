import sys,shutil,time,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.daily_editorial import publish_ticket
root=runtime.BASE/'runs/creation-1793057266-6659e9ab'
with process_lock(root/'api/worker.lock',blocking=False):
 assert recovery.safe_original(root)
 p=root/'queue/d7852ca98af3a79f02ee3b3f/ticket.json';t=runtime.read(p)
 assert t['state']=='needs_attention' and t['error']=='API generation rejected: invalid_response'
 base=Path('/opt/monitor/geo-content/maintenance/recovery-20261027/invalid-response-before');base.mkdir(exist_ok=True)
 shutil.copy2(p,base/'ticket.json')
 replacement=publish_ticket(root,t['stage'],root/t['location'],list(t['inputs']),t['outputs'],{**t['meta'],'revision':1,'replaces':t['id'],'recovery_invalid_response':True})
 atomic_json(p,{**t,'state':'revision_requested','replaced_by':replacement})
 day=root/'days/2026-10-27/day.json';shutil.copy2(day,base/'day.json');atomic_json(day,{**runtime.read(day),'status':'producing'})
 runtime.resume(root,check_balance=False);recovery.succeeded(root)
 print(json.dumps({'retry':replacement,'reason':'Known completed response was malformed JSON; one explicit retry under unchanged article cap'}))

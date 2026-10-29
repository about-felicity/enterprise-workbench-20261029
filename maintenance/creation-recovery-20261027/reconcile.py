import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
from geo_source_cards.runtime import process_lock,atomic_json
for root in (runtime.BASE/'runs').iterdir():
 j=runtime.read(root/'job.json')
 if j.get('date','')<'2026-10-26' or runtime.read(root/'control.json').get('reason')=='plan_deleted':continue
 active=runtime.read(root/'api/active.json');t=runtime.read(root/'queue'/active.get('ticket','')/'ticket.json')
 if t.get('recovery_reason') and t.get('state') in {'accepted','revision_requested'} and recovery.safe_original(root):
  try:
   with process_lock(root/'api/worker.lock',blocking=False):
    atomic_json(root/'api/active.json',{**active,'state':'SUBMITTED','manual_recovery':'Article delivered from saved response; no send retry'})
    runtime.resume(root,check_balance=False);print('reconciled',root.name)
  except Exception as e:print('deferred',root.name,str(e)[:150])

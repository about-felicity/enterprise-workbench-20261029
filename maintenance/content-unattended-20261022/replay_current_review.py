"""Rebind a fully received review after the sentence-map recovery fix, no resend."""
import sys,json,hashlib,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.known_response import load
from geo_source_cards.api_worker import materialize
from geo_source_cards.daily_editorial import publish_ticket
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended');marker=D/'review-map-replay.json'
assert not marker.exists(),'Already published'
root=runtime.job_root('creation-1792575159-0a8f9221');old=runtime.read(root/'queue/79bb96ff674b24f4a4c17c79/ticket.json')
source=root/'api/runs'/old['execution']['run_id'];location=root/old['location']
assert old.get('error')=='Review belongs to another draft'
proof=runtime.read(source/'known_response.json')
if runtime.read(source/'logic-call/api_state.json').get('state')=='RESPONDED':
 proof.update(logic_source_run=source.name,logic_response_sha256=hashlib.sha256((source/'logic-call/response.json').read_bytes()).hexdigest())
preview=D/'review-map-preview';shutil.copytree(source,preview)
atomic_json(preview/'known_response.json',proof)
answer=load(root,old,preview);materialize(old,preview,answer)
result=runtime.read(preview/'result.json')
assert result.get('draft_sha256')==hashlib.sha256((location/'draft.md').read_bytes()).hexdigest()
with process_lock(root/'coordinator.lock',blocking=True):
 for name,expected in old['inputs'].items():
  if name=='known_response.json':continue
  assert hashlib.sha256((location/name).read_bytes()).hexdigest()==expected,name
 atomic_json(location/'known_response.json',proof)
 meta={**old['meta'],'revision':1,'replaces':old['id'],'known_response_replay':True,'review_map_recovery':'v5'}
 ticket=publish_ticket(root,'review',location,list(old['inputs']),['result.json'],meta)
 atomic_json(root/'queue'/old['id']/'ticket.json',{**old,'state':'revision_requested','replaced_by':ticket})
atomic_json(marker,{'at':time.time(),'ticket':ticket,'source':source.name,'new_paid_requests':0,
 'logic_status':answer.get('logic_review',{}).get('status'),'fact_failures':answer.get('failures',[])})
print(json.dumps(runtime.read(marker),ensure_ascii=False))

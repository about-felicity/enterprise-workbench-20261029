"""Retry a proven unsent audit with a smaller equivalent evidence payload."""
import sys,json,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.daily_editorial import publish_ticket
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');marker=D/'compact-review-published.json'
assert not marker.exists(),'Already published'
assert runtime.read(D/'review-affordability.json').get('affordable')
root=runtime.job_root('creation-1792575159-0a8f9221');tid=runtime.read(D/'pilot-review-published.json')['ticket']
with process_lock(root/'coordinator.lock',blocking=True):
 old=runtime.read(root/'queue'/tid/'ticket.json');run=root/'api/runs'/old['execution']['run_id']
 assert runtime.read(root/'queue'/tid/'receipt.json').get('error_code')=='article_budget_exceeded'
 assert runtime.read(run/'preflight_rejection.json').get('request_sent') is False
 assert not (run/'call/response.json').is_file()
 ticket=publish_ticket(root,'review',root/old['location'],list(old['inputs']),['result.json'],{
     **old['meta'],'revision':1,'replaces':old['id'],'compiler_review_release':'compact-v2','known_response_replay':False})
 atomic_json(root/'queue'/tid/'ticket.json',{**old,'state':'revision_requested','replaced_by':ticket})
atomic_json(marker,{'at':time.time(),'ticket':ticket,'old_request_was_not_sent':True,'budgets_changed':False})
print(json.dumps(runtime.read(marker)))

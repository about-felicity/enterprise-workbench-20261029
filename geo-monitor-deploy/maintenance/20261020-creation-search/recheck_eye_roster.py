"""Recheck the same completed delivery under a corrected local roster validator."""
import json,shutil,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
from geo_source_cards.daily_editorial import receive
from geo_source_cards.daily_editorial import file_hash
from geo_source_cards.staged_editorial import check,research_for_writer
root=runtime.job_root('creation-1792479954-8a96bc88');control=runtime.read(root/'control.json')
assert control.get('reason')=='roster_validator_update' and control.get('paused')
assert runtime.read(root/'api/active.json').get('state')=='SUBMITTED'
job=runtime.read(root/'job.json');assert not runtime.read(studio.day_path(job['studio_plan_id'],job['date'])).get('paused')
ticket=root/'queue/8ea9160604b6d844ac7269c6';t=runtime.read(ticket/'ticket.json');receipt=runtime.read(ticket/'receipt.json')
assert t['state'] in ('needs_attention','claimed') and '标题款数' in t.get('error','')
assert receipt['state']=='completed' and receipt['execution']==t['execution']
writer=root/t['location'];decision=check(research_for_writer(writer),writer);assert not decision['failures'],decision
backup=root/'repair_evidence/validator-roster-v1'
if not backup.exists():
 backup.mkdir(parents=True);shutil.copytree(ticket,backup/'ticket')
# Local checks update writing_job status. Restore the exact immutable input
# snapshot before rechecking the same receipt, rather than changing its hashes.
run=root/'api/runs'/t['execution']['run_id']
for name,expected in t['inputs'].items():
 if name in t['outputs'] or file_hash(writer/name)==expected:continue
 assert file_hash(run/name)==expected,('Immutable input mismatch',name)
 shutil.copy2(writer/name,backup/(name+'.before-recheck'))
 shutil.copy2(run/name,writer/name)
runtime.atomic_json(ticket/'ticket.json',{**t,'state':'claimed'})
receive(root,ticket)
runtime.atomic_json(backup/'local_recheck.json',{'at':time.time(),'reason':'Question heading was incorrectly counted as a product; same completed delivery passes corrected validator','provider_requests':0,'receipt_unchanged':runtime.read(ticket/'receipt.json')==receipt,'decision':decision})
runtime.resume(root)
print(json.dumps({'ticket':t['id'],'state':runtime.read(ticket/'ticket.json')['state'],'new_provider_requests':0,'independent_review':'queued'},ensure_ascii=False))

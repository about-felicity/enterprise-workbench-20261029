"""Publish only locally ready drafts for their still-required independent audit."""
import sys,json,time,hashlib,shutil
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.staged_editorial import check,research_for_writer
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended');marker=D/'ready-reviews.json'
assert not marker.exists(),'Already published'
published=[]
for row in runtime.read(D/'current-gates.json')['articles']:
 if row.get('error') or row.get('failures'):continue
 root=runtime.job_root(row['job']);writer=root/'days/2026-10-21/jobs'/row['category']/f"{row['number']:02d}"/'writer';review=writer.parent/'review'
 assert runtime.read(root/'control.json').get('reason')=='deployment_drain'
 assert runtime.read(root/'api/active.json').get('state') in (None,'SUBMITTED')
 with process_lock(root/'coordinator.lock',blocking=True):
  assert not check(research_for_writer(writer),writer)['failures']
  jobs=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
  matching=[j for j in jobs if (j['meta'].get('category'),j['meta'].get('number'))==(row['category'],row['number'])]
  old=max(matching,key=lambda j:j.get('created_at',''))
  assert all(j['state']!='claimed' for j in matching)
  saved=D/'before-ready-reviews'/root.name/row['category']/str(row['number']);shutil.copytree(writer.parent,saved)
  review.mkdir(exist_ok=True);inputs=['task.md','draft.md','knowledge.json','product.json','category.json']
  for n in inputs[1:]:shutil.copy2(writer/n,review/n)
  if not (review/'task.md').is_file():atomic_write(review/'task.md','独立审核全文事实、主题、体裁、衔接和结论。必须逐项指出问题，不因完成而通过。')
  if runtime.read(writer/'writer_done.json').get('paragraph_repair_audit'):
   for n in ('writer_done.json','paragraph_repair.json'):shutil.copy2(writer/n,review/n);inputs.append(n)
  known=None
  for source in sorted(matching,key=lambda j:j.get('created_at',''),reverse=True):
   run=root/'api/runs'/source.get('execution',{}).get('run_id','missing')
   if source.get('stage')!='review' or runtime.read(run/'call/api_state.json').get('state')!='RESPONDED':continue
   if all((review/n).is_file() and hashlib.sha256((review/n).read_bytes()).hexdigest()==h for n,h in source['inputs'].items()):
    known={'source_run':run.name,'source_ticket':source['id'],'response_sha256':hashlib.sha256((run/'call/response.json').read_bytes()).hexdigest()};break
  if known:atomic_json(review/'known_response.json',known);inputs.append('known_response.json')
  meta={**old['meta'],'revision':1,'replaces':old['id'],'known_response_replay':bool(known),'review_release':'current-gates-v4'}
  ticket=publish_ticket(root,'review',review,list(dict.fromkeys(inputs)),['result.json'],meta)
  for prior in matching:
   if prior['state'] in {'pending','needs_attention'}:atomic_json(root/'queue'/prior['id']/'ticket.json',{**prior,'state':'revision_requested','replaced_by':ticket,'operator_reason':'Current local checks passed; audit current draft rather than rewriting it'})
  published.append({**row,'ticket':ticket,'reused_complete_fact_response':bool(known)})
atomic_json(marker,{'at':time.time(),'articles':published,'budget_limits_changed':False})
for identity in sorted({r['job'] for r in published}):runtime.resume(runtime.job_root(identity))
print(json.dumps(runtime.read(marker),ensure_ascii=False))

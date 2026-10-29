"""Preserve a budget-rejected unsent writer and independently rereview its draft."""
import hashlib,json,shutil,sqlite3,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
from geo_source_cards.api_worker import Worker
from geo_source_cards.daily_editorial import publish_ticket
root=runtime.job_root('creation-1792479954-8a96bc88');job=runtime.read(root/'job.json')
control=runtime.read(root/'control.json');assert control.get('reason')=='budget_exceeded' and control.get('paused')
assert job['budget_limits']=={'article_budget_cny':.35,'task_budget_cny':5.25}
assert not runtime.read(studio.day_path(job['studio_plan_id'],job['date'])).get('paused')
active=runtime.read(root/'api/active.json');assert active['state']=='REQUESTING'
ticket=root/'queue'/active['ticket'];t=runtime.read(ticket/'ticket.json');run=root/'api/runs'/active['run_id']
assert t['stage']=='writer' and t['meta']['number']==1 and not list((run/'call').glob('*'))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 identity=hashlib.sha256(str((run/'call').resolve()).encode()).hexdigest()
 assert db.execute('select count(*) from costs where id=?',(identity,)).fetchone()[0]==0
archive=root/'repair_evidence/budget-unsent-review-contract-v1';assert not archive.exists();archive.mkdir(parents=True)
shutil.copytree(ticket,archive/'ticket');shutil.copytree(run,archive/'run')
engine=Worker(root,None);engine.failed(t,active,'budget_pre_send_rejection',detail='No request or API state was written and no reservation exists; preserve unsent intent, independently recheck existing draft after prompt conflict correction')
writer=root/t['location'];review=writer.parent/'review-contract-recheck-v1';review.mkdir()
for name in ('draft.md','knowledge.json','product.json','category.json'):shutil.copy2(writer/name,review/name)
shutil.copy2(writer.parent/'review/task.md',review/'task.md')
new=publish_ticket(root,'review',review,['task.md','draft.md','knowledge.json','product.json','category.json'],['result.json'],{**t['meta'],'replaces':t['id'],'review_contract_recheck':1})
latest=runtime.read(ticket/'ticket.json');runtime.atomic_json(ticket/'ticket.json',{**latest,'state':'revision_requested','replaced_by':new,'operator_reason':'Known unsent writer deferred; existing unchanged draft is independently reviewed under explicit section-role contract'})
runtime.atomic_json(archive/'decision.json',{'at':time.time(),'known_unsent_writer':t['id'],'independent_review':new,'draft_unchanged':True,'article_budget_cny':.35,'task_budget_cny':5.25})
runtime.resume(root)
print(json.dumps({'preserved_unsent_writer':t['id'],'new_review':new,'writer_resends':0,'limits_unchanged':True},ensure_ascii=False))

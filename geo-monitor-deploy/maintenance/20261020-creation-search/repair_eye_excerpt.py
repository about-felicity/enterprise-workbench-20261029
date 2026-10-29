import hashlib,json,shutil,sqlite3,sys,time
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
from geo_source_cards.api_worker import Worker
from geo_source_cards.daily_editorial import repair_research
root=runtime.job_root('creation-1792479954-8a96bc88');job=runtime.read(root/'job.json')
assert runtime.read(root/'control.json').get('reason')=='material_or_quality_check'
assert not runtime.read(studio.day_path(job['studio_plan_id'],job['date'])).get('paused')
active=runtime.read(root/'api/active.json');t=runtime.read(root/'queue'/active['ticket']/'ticket.json');run=root/'api/runs'/active['run_id']
assert active['state'] in ('REQUESTING','SUBMITTED') and t['stage']=='research' and t['meta']['number']==8
assert not list((run/'call').glob('*'))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 assert not db.execute('select 1 from costs where id=?',(hashlib.sha256(str((run/'call').resolve()).encode()).hexdigest(),)).fetchone()
archive=root/'repair_evidence/excerpt-pre-send-v1'
if not archive.exists():
 shutil.copytree(run,archive/'run')
 Worker(root,None).failed(t,active,'source_preflight_rejected',detail='Product-description paragraph was incorrectly treated as a heading; prompt building failed before provider request')
else:assert runtime.read(root/'queue'/t['id']/'receipt.json').get('error_code')=='source_preflight_rejected'
generated=[]
for path in (root/'queue').glob('*/ticket.json'):
 row=runtime.read(path)
 if row['meta'].get('replaces')==t['id']:
  assert row['state']=='pending' and not row.get('execution');generated.append((path,row))
result=repair_research(root,t,'已核对原文全文：主要功效、核心成分、使用感受是上一款产品的描述，不能拆成新产品；标题里的“第一名的眼霜”也不是产品。按修正后的通用提取器重建名单和逐字证据，保留原会话、来源合同及所有费用。')
for path,row in generated:
 shutil.copytree(path.parent,archive/('unused-retry-'+row['id']))
 runtime.atomic_json(path,{**row,'state':'revision_requested','replaced_by':result['ticket'],'operator_reason':'Unsent retry with old extraction replaced by corrected source snapshot'})
runtime.atomic_json(archive/'decision.json',{'at':time.time(),'original_provider_requests':0,'result':result,'article_budget_cny':job['budget_limits']['article_budget_cny']})
runtime.resume(root);print(json.dumps(result,ensure_ascii=False))

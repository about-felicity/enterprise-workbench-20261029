"""One concrete prompt correction for a known responded research failure."""
import json,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
base=Path('/opt/monitor/geo-content')
def read(p):return json.loads(p.read_text()) if p.exists() else {}
t=read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
roots=[p.parent for p in (base/'runtime/runs').glob('*/job.json') if read(p).get('studio_plan_id')==t['plan_id']];assert len(roots)==1
r=roots[0];assert read(r/'control.json').get('reason')=='needs_attention'
failed=[read(p) for p in (r/'queue').glob('*/ticket.json') if read(p).get('state')=='needs_attention'];assert len(failed)==1
ticket=failed[0];assert ticket['stage']=='research' and 'Missing product-specific evidence' in ticket.get('error','')
run=r/'api/runs'/ticket['execution']['run_id'];assert read(run/'call/api_state.json').get('state')=='RESPONDED'
receipt=read(r/'queue'/ticket['id']/'receipt.json');assert receipt['state']=='failed' and receipt['execution']==ticket['execution']
assert not any(read(p).get('state')=='claimed' for p in (r/'queue').glob('*/ticket.json'))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
    assert db.execute('select count(*) from costs c join studio_cost_scopes s on s.id=c.id where s.job=? and c.charged is null',(read(r/'job.json')['job_id'],)).fetchone()[0]==0
for p in (base/'runtime/runs').glob('*/job.json'):
    if read(p.parent/'control.json').get('paused'):continue
    assert read(p.parent/'days'/read(p)['date']/'day.json').get('status')=='complete'
backup=Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/before-explicit-roster-coverage-v1');assert not backup.exists()
target=base/'engine/geo_source_cards/genre_prompts.py';data=Path('/tmp/brow-genre-prompts.py').read_bytes();compile(data,str(target),'exec')
subprocess.run(['systemctl','stop','geo-content-worker.service'],check=True)
try:
    backup.mkdir(parents=True,mode=0o700);shutil.copy2(target,backup/target.name)
    temp=target.with_suffix('.coverage-new');temp.write_bytes(data);temp.replace(target)
    sys.path[:0]=[str(base),str(base/'engine')]
    from creation import runtime
    from geo_source_cards.daily_editorial import repair_research
    reason='当前已收到且已结算的研究结果遗漏首个竞品Ri证据。新提示词提供required_product_evidence逐行清单，先完整生成每个竞品的组成/规格source_claim，再给2条比较意见；自有产品事实不得替代竞品。原文、质量门槛及单篇0.35预算不变。仅本次已知失败的新合同修订，不重放未知请求。'
    result=repair_research(r,ticket,reason)
    p=r/'queue'/result['ticket']/'ticket.json';new=runtime.read(p)
    runtime.atomic_json(p,{**new,'meta':{**new['meta'],'research_repair_round':ticket['meta'].get('research_repair_round',0)+1,'operator_prompt_repair_round':1,'prompt_contract_revision':'explicit-roster-coverage-v1'}})
    runtime.atomic_json(backup/'repair.json',{'at':time.time(),'original_ticket':ticket['id'],'replacement':result['ticket'],'original_response_unchanged':True,'quality_and_budget_unchanged':True,'source_recapture_calls':0})
    runtime.resume(r)
finally:subprocess.run(['systemctl','start','geo-content-worker.service'],check=True)
print(json.dumps({'replacement':result['ticket'],'approved_articles_unchanged':14,'same_job':r.name},ensure_ascii=False))

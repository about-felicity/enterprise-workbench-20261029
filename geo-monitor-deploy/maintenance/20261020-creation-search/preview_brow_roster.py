import json,shutil,sys
from pathlib import Path
sys.path[:0]=['/tmp/brow-scope-qa/engine','/opt/monitor/geo-content']
from creation import runtime
from geo_source_cards.daily_editorial import prepare_day
from geo_source_cards.api_worker import Worker
t=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
roots=[p.parent for p in (runtime.BASE/'runs').glob('*/job.json') if runtime.read(p).get('studio_plan_id')==t['plan_id']];assert len(roots)==1
r=roots[0];assert runtime.read(r/'control.json').get('reason')=='source_quality_review'
out=Path('/tmp/brow-roster-preview');out.mkdir(exist_ok=False)
for name in ['job.json','product.json','geo_articles.jsonl','article_goal.json','draft_policy.json']:
    if (r/name).exists():shutil.copy2(r/name,out/name)
j=runtime.read(out/'job.json');prepare_day(out,out/'geo_articles.jsonl',out/'product.json',j['date'],max_per_category=max(j['max_per_category'],j['article_target']))
class NoPaidCalls:
    def complete(self,*args,**kwargs):raise AssertionError('Preview must not send paid requests')
result=Worker(out,NoPaidCalls()).once(j['date'])
assert result['status']=='accepted',result
allocation=runtime.read(out/'days'/j['date']/'article_allocation.json')
assert allocation['planned']==15 and not allocation['shortfall'] and all(allocation['selected'].values()),allocation
print(json.dumps({'result':result,'selected':{k:len(v) for k,v in allocation['selected'].items()},'shortfall':allocation['shortfall'],'paid_calls':0},ensure_ascii=False))

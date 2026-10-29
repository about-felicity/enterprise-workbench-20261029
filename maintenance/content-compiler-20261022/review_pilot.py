"""Audit the complete pilot draft after style-only failures became warnings."""
import sys,json,time,shutil
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.staged_editorial import check,research_for_writer
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.runtime import atomic_json,process_lock,atomic_write
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');marker=D/'pilot-review-published.json'
assert not marker.exists(),'Already sent to review'
root=runtime.job_root('creation-1792575159-0a8f9221');writer=root/'days/2026-10-21/compiler-pilots/测评类/02/writer';review=writer.parent/'review'
result=check(research_for_writer(writer),writer)
assert not result['failures'],result['failures']
with process_lock(root/'coordinator.lock',blocking=True):
 jobs=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 matching=[j for j in jobs if j['meta'].get('compiler_pilot_release')=='practical-v1' and (j['meta'].get('category'),j['meta'].get('number'))==('测评类',2)]
 assert all(j['state'] not in {'pending','claimed'} for j in matching)
 old=max(matching,key=lambda j:j['created_at']);review.mkdir(exist_ok=True)
 for name in ('draft.md','knowledge.json','product.json','category.json','writer_done.json'):shutil.copy2(writer/name,review/name)
 atomic_write(review/'task.md','独立审核当前正文的事实、论证和前后顺序；普通选购意见无需产品试验，具体产品属性及数字须有来源；保留真实问题，不因格式完整就通过。')
 meta={**old['meta'],'revision':1,'replaces':old['id'],'known_response_replay':False}
 tid=publish_ticket(root,'review',review,['task.md','draft.md','knowledge.json','product.json','category.json','writer_done.json'],['result.json'],meta)
 atomic_json(root/'queue'/old['id']/'ticket.json',{**old,'state':'revision_requested','replaced_by':tid,'operator_reason':'Style repetition is advisory; audit existing complete draft without another writer call'})
atomic_json(marker,{'at':time.time(),'ticket':tid,'new_writer_calls':0,'warnings':result.get('warnings',[])})
print(json.dumps(runtime.read(marker),ensure_ascii=False))

"""Review only the four already-delivered drafts missed by response-only reuse."""
import sys,time,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,quality_repair as q
from geo_source_cards.runtime import process_lock,atomic_json
class ReviewOnly(q.CreationClient):
 def complete(self,*args,**kwargs):
  if kwargs.get('stage')!='review':raise ValueError('已送达稿件仅允许复用并审稿；未授权重复writer请求')
  return super().complete(*args,**kwargs)
with process_lock(q.ROOT/'process.lock',blocking=False):
 report={'started_at':time.time(),'results':[]};path=q.ROOT/'delivered-recovery-20261021.json'
 q.CreationClient=ReviewOnly;q.STOP_ON_UNKNOWN=True;q.STOP.clear()
 for item in q.scan():
  status=runtime.read(q.ROOT/item['key']/'status.json')
  if status.get('reason')!='已送达稿件仅允许复用并审稿；未授权重复writer请求':continue
  assert not any(runtime.read(p).get('state') in {'REQUEST_UNKNOWN','REQUESTING'} and not p.with_name('response.json').exists() for p in (q.ROOT/item['key']).glob('attempt-*/calls/*/api_state.json'))
  control=Path(item['root'])/'control.json';before=control.read_bytes() if control.exists() else None
  result=q.revise(item,retry_known=True)
  after=control.read_bytes() if control.exists() else None
  report['results'].append({'key':item['key'],**result,'original_job_control_unchanged':before==after})
  atomic_json(path,report);print(json.dumps(report['results'][-1],ensure_ascii=False),flush=True)
  if q.STOP.is_set() or before!=after:report['stopped_for_attention']=True;break
 report['finished_at']=time.time();atomic_json(path,report)

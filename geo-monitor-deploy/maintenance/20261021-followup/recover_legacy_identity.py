"""Recover only proved-unsent holds and locally passing identity-only failures."""
import json,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,quality_repair as q
from geo_source_cards.consumer_prompts import require_writer_material,evidence_units
from geo_source_cards.runtime import atomic_json,process_lock
R=q.ROOT
class ReviewOnlyClient(q.CreationClient):
 def complete(self,*args,**kwargs):
  if kwargs.get('stage')!='review':raise ValueError('已送达稿件仅允许复用并审稿；未授权重复writer请求')
  return super().complete(*args,**kwargs)

def main():
 report={'started_at':time.time(),'selected':[],'excluded':[],'results':[]}
 target=R/'identity-recovery-20261021.json'
 with process_lock(R/'process.lock',blocking=False):
  inventory={i['key']:i for i in q.scan()}
  original=runtime.read(R/'followup-paused-20261021.json')['selected']
  held={i['key']:i for i in runtime.read(R/'identity-preflight-hold.json')['held']}
  for item in original:
   entry=R/item['key'];status=runtime.read(entry/'status.json');reason=None;mode=None
   if status.get('state')=='complete':continue
   if any(runtime.read(p).get('state') in {'REQUEST_UNKNOWN','REQUESTING'} and not p.with_name('response.json').exists() for p in entry.glob('attempt-*/calls/*/api_state.json')):reason='unknown_request_never_replayed'
   if not reason and runtime.read(Path(item['root'])/'approved'/item['id']/'receipt.json').get('word_sha256')!=item['original_word_sha256']:reason='original_version_changed'
   if not reason:
    writer=Path(item['writer'])
    try:require_writer_material(runtime.read(writer/'knowledge.json'),runtime.read(writer/'product.json'),evidence_units(writer))
    except (ValueError,KeyError,TypeError) as e:reason=str(e)
   if not reason and item['key'] in held:
    side=entry/f"attempt-{held[item['key']]['attempt']}"
    if any(side.glob('calls/*/request.json')) or any(side.glob('calls/*/api_state.json')):reason='hold_has_request_evidence'
    else:mode='proved_unsent_hold'
   elif not reason and '自有产品' in status.get('reason',''):
    side=entry/f"attempt-{status.get('attempt',0)}";bases=list(side.glob('days/*/articles/*/*/writer'))
    if len(bases)!=1:reason='no_single_delivered_writer'
    else:
     try:
      checked=q.check(bases[0].parent/'research',bases[0])
      if checked['failures']:reason='other_quality_failures_remain'
      else:mode='reuse_delivered_writer_review_only'
     except (ValueError,KeyError,FileNotFoundError) as e:reason=str(e)
   elif not reason:reason='not_an_identity_only_failure_or_unsent_hold'
   if reason:report['excluded'].append({'key':item['key'],'reason':reason})
   else:report['selected'].append({'key':item['key'],'mode':mode})
  atomic_json(target,report)
  q.STOP.clear();q.STOP_ON_UNKNOWN=True;normal=q.CreationClient
  for candidate in report['selected']:
   item=inventory[candidate['key']];control=Path(item['root'])/'control.json';before=control.read_bytes() if control.exists() else None
   q.CreationClient=ReviewOnlyClient if candidate['mode']=='reuse_delivered_writer_review_only' else normal
   try:result=q.revise(item,retry_known=True)
   finally:q.CreationClient=normal
   after=control.read_bytes() if control.exists() else None
   report['results'].append({**candidate,**result,'original_job_control_unchanged':before==after})
   atomic_json(target,report);print(json.dumps(report['results'][-1],ensure_ascii=False),flush=True)
   if q.STOP.is_set() or before!=after:report['stopped_for_attention']=True;break
  report['finished_at']=time.time();atomic_json(target,report)
 print(json.dumps({'selected':len(report['selected']),'processed':len(report['results']),'stopped_for_attention':report.get('stopped_for_attention',False)},ensure_ascii=False))
if __name__=='__main__':main()

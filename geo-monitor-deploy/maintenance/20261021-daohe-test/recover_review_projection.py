"""Reprocess known complete paid research after a deterministic outline fix.

Uses normal execution authorization, materialization, evidence/outline validation
and queue receipt handling. It never instantiates a completion client or changes
an original response, source or input manifest.
"""
import sys,json,hashlib,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.api_worker import Worker
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.execution_runs import authorize
from geo_source_cards.runtime import atomic_json
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');root=runtime.job_root('creation-1792576129-389f575e')
assert runtime.read(root/'control.json').get('paused')
assert not (root/'api/active.json').exists()
results=[]
for oldpath in sorted((root/'queue').glob('*/ticket.json')):
 old=runtime.read(oldpath)
 if old['stage']!='research' or old['state']!='needs_attention' or '测评稿缺少统一比较维度' not in old.get('error',''):continue
 oldrun=root/'api/runs'/old['execution']['run_id'];source=oldrun/'call/response.json'
 assert runtime.read(oldrun/'call/api_state.json').get('state')=='RESPONDED' and source.exists()
 answer=runtime.read(source);assert 'units' in answer and 'angle' in answer
 oldlocation=root/old['location'];location=oldlocation.parent/('research-local-projection-'+old['id'])
 if not location.exists():shutil.copytree(oldlocation,location)
 inputs=['research_input.json','research_task.txt']
 meta={**old['meta'],'local_projection_of':old['id'],'replaces':old['id']}
 tid=publish_ticket(root,'research',location,inputs,['research_result.json'],meta)
 w=Worker(root,None,target_article=tuple(old['meta'].get(k) for k in ('date','category','number')))
 selected=w.select('2026-10-21');assert selected['id']==tid
 active=runtime.read(root/'api/active.json');job=authorize(root,tid,w.identity,active['run_id']);active.update(state='RESPONDED',execution=job['execution'])
 run=root/'api/runs'/active['run_id'];run.mkdir(parents=True,exist_ok=True)
 for name in inputs:shutil.copyfile(location/name,run/name)
 atomic_json(run/'answer.json',answer)
 proof={'recovered_from_run':oldrun.name,'source_response_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'reason':'Repair deterministic review outline role projection; all original evidence retained','new_paid_calls':0,'at':time.time()}
 atomic_json(run/'local_response_reuse.json',proof);atomic_json(root/'api/active.json',active)
 result=w.finish(job,active)
 assert result['status']=='accepted',result
 atomic_json(oldpath,{**old,'state':'revision_requested','replaced_by':tid,'local_response_reuse':proof})
 # Normal worker archives a submitted active receipt on its next pass. Archive
 # here while the job stays paused, before selecting the next local projection.
 activefile=root/'api/active.json';history=root/'api/history'/(active['run_id']+'.json');history.parent.mkdir(exist_ok=True);activefile.replace(history)
 results.append({'old_ticket':old['id'],'new_ticket':tid,'number':old['meta']['number'],'status':result['status'],**proof})
atomic_json(M/'review-local-recovery.json',results)
runtime.resume(root)
print(json.dumps({'recovered':len(results),'new_paid_calls':0,'results':results},ensure_ascii=False))

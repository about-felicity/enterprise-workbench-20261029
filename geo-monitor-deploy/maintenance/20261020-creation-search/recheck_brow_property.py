"""Supersede local validation of one durable response; no provider replay."""
import hashlib,json,shutil,sqlite3,subprocess,sys,time
from datetime import datetime
from pathlib import Path
base=Path('/opt/monitor/geo-content')
def read(p):return json.loads(p.read_text()) if p.exists() else {}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
task=read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
roots=[p.parent for p in (base/'runtime/runs').glob('*/job.json') if read(p).get('studio_plan_id')==task['plan_id']];assert len(roots)==1
r=roots[0];control=read(r/'control.json');assert control.get('reason')=='needs_attention'
failed=[read(p) for p in (r/'queue').glob('*/ticket.json') if read(p).get('state')=='needs_attention'];assert len(failed)==1
t=failed[0];assert t['stage']=='research' and 'Missing product-specific evidence' in t.get('error','')
run=r/'api/runs'/t['execution']['run_id'];assert read(run/'call/api_state.json').get('state')=='RESPONDED'
call_hashes={p.name:sha(p) for p in (run/'call').iterdir() if p.is_file()}
receipt=r/'queue'/t['id']/'receipt.json';old_receipt=read(receipt);assert old_receipt['state']=='failed' and old_receipt['execution']==t['execution']
assert not any(read(p).get('state')=='claimed' for p in (r/'queue').glob('*/ticket.json'))
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
    assert db.execute('select count(*) from costs c join studio_cost_scopes s on s.id=c.id where s.job=? and c.charged is null',(read(r/'job.json')['job_id'],)).fetchone()[0]==0
for p in (base/'runtime/runs').glob('*/job.json'):
    if read(p.parent/'control.json').get('paused'):continue
    assert read(p.parent/'days'/read(p)['date']/'day.json').get('status')=='complete'
backup=Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/before-neutral-property-v1');assert not backup.exists()
archive=r/'repair_evidence/neutral-property-local-recheck-v1';assert not archive.exists()
subprocess.run(['systemctl','stop','geo-content-worker.service'],check=True)
try:
    assert read(r/'control.json')==control
    backup.mkdir(parents=True,mode=0o700)
    for name,source in [('genre_outline.py','/tmp/brow-genre-outline.py'),('api_worker.py','/tmp/brow-api-worker.py')]:
        target=base/'engine/geo_source_cards'/name;data=Path(source).read_bytes();compile(data,str(target),'exec')
        shutil.copy2(target,backup/name);temp=target.with_suffix('.property-new');temp.write_bytes(data);temp.replace(target)
    sys.path[:0]=[str(base),str(base/'engine')]
    from creation import runtime
    from geo_source_cards.api_worker import Worker
    class NoPaidCalls:
        def complete(self,*args,**kwargs):raise AssertionError('Local recheck cannot send provider requests')
    worker=Worker(r,NoPaidCalls());assert worker.identity==t['client']
    archive.mkdir(parents=True,mode=0o700);shutil.copy2(r/'queue'/t['id']/'ticket.json',archive/'failed-ticket.json')
    receipt.rename(archive/'failed-receipt.json')
    claimed={**t,'state':'claimed','local_validation_revision':'neutral-property-v1'}
    runtime.atomic_json(r/'queue'/t['id']/'ticket.json',claimed)
    active={'ticket':t['id'],'run_id':t['execution']['run_id'],'state':'RESPONDED','stage':'research','execution':t['execution'],'started_epoch':datetime.fromisoformat(t['claimed_at']).timestamp(),'local_rechecked_epoch':time.time()}
    runtime.atomic_json(r/'api/active.json',active)
    result=worker.finish(claimed,active)
    assert result['status']=='accepted',result
    assert {p.name:sha(p) for p in (run/'call').iterdir() if p.is_file()}==call_hashes
    note={'at':time.time(),'ticket':t['id'],'original_response_files_unchanged':call_hashes,'superseded_local_receipt_sha256':sha(archive/'failed-receipt.json'),'new_local_receipt_sha256':sha(receipt),'new_provider_requests':0,'source_contract_unchanged':True,'risk_unit_preserved':True,'projection':runtime.read(run/'research_projection.json')}
    runtime.atomic_json(archive/'recheck.json',note)
    runtime.resume(r)
finally:subprocess.run(['systemctl','start','geo-content-worker.service'],check=True)
print(json.dumps({'result':result,'new_provider_requests':0,'original_api_response_unchanged':True,'independent_writer_and_review':'queued'},ensure_ascii=False))

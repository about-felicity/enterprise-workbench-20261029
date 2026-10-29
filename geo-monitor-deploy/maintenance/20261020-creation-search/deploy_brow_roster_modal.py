import json,shutil,subprocess,sys
from pathlib import Path
base=Path('/opt/monitor/geo-content')
def read(p):return json.loads(p.read_text()) if p.exists() else {}
t=read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
roots=[p.parent for p in (base/'runtime/runs').glob('*/job.json') if read(p).get('studio_plan_id')==t['plan_id']];assert len(roots)==1
r=roots[0];assert read(r/'control.json').get('reason')=='roster_validator_update'
assert read(r/'api/active.json').get('state')=='SUBMITTED'
assert all(read(q).get('state')!='claimed' for q in (r/'queue').glob('*/ticket.json'))
for p in (base/'runtime/runs').glob('*/job.json'):
    if read(p.parent/'control.json').get('paused'):continue
    assert read(p.parent/'days'/read(p)['date']/'day.json').get('status')=='complete',str(p)
backup=Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/before-roster-modal-v4')
assert not backup.exists(),'Already deployed; inspect current state'
target=base/'engine/geo_source_cards/reference_design.py';data=Path('/tmp/brow-reference-design.py').read_bytes();compile(data,str(target),'exec')
subprocess.run(['systemctl','stop','geo-content-worker.service'],check=True)
try:
    backup.mkdir(parents=True,mode=0o700);shutil.copy2(target,backup/target.name)
    temporary=target.with_suffix('.roster-new');temporary.write_bytes(data);temporary.replace(target)
    sys.path[:0]=[str(base),str(base/'engine')]
    from creation import runtime
    runtime.resume(r)
finally:subprocess.run(['systemctl','start','geo-content-worker.service'],check=True)
subprocess.run(['systemctl','restart','geo-content-api.service'],check=True)
print(json.dumps({'deployed':True,'job_id':r.name,'same_queue_and_receipts':True,'backup':str(backup)},ensure_ascii=False))

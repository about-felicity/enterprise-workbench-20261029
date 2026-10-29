"""One-time repair at a verified, settled boundary; never a daily recovery script."""
import json,shutil,sqlite3,subprocess,sys,time,zipfile
from pathlib import Path
base=Path('/opt/monitor/geo-content')
def read(p):return json.loads(p.read_text()) if p.exists() else {}
t=read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
roots=[p.parent for p in (base/'runtime/runs').glob('*/job.json') if read(p).get('studio_plan_id')==t['plan_id']];assert len(roots)==1
r=roots[0];job=read(r/'job.json');backup=r/'revisions/source-scope-v1'
code_backup=Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/before-source-scope')
assert not backup.exists() and not code_backup.exists(),'Already applied; inspect rather than rerun'
def settled():
    assert read(r/'control.json').get('reason')=='source_quality_review'
    assert read(r/'api/active.json').get('state')=='SUBMITTED'
    for p in (r/'api').rglob('api_state.json'):
        state=read(p)
        if state.get('state')=='RESPONDED':continue
        answer=read(p.parent/'answer.json')
        assert state.get('state')=='INVALID_RESPONSE' and state.get('error_type')=='JSONDecodeError',str(p)
        assert answer.get('finish_reason')=='stop' and isinstance(answer.get('content'),str) and answer.get('usage'),str(p)
        with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
            row=db.execute('select state,charged from costs where id=?',(state.get('reservation'),)).fetchone()
        assert row and row[0]=='settled' and row[1] is not None,str(p)
    for p in (r/'queue').glob('*/ticket.json'):assert read(p).get('state')!='claimed',str(p)
    for p in (base/'runtime/runs').glob('*/job.json'):
        if read(p.parent/'control.json').get('paused'):
            if read(p.parent/'control.json').get('reason')=='brow_scope_maintenance':
                assert read(p.parent/'api/active.json').get('state') in (None,'SUBMITTED'),str(p)
                assert all(read(q).get('state')!='claimed' for q in (p.parent/'queue').glob('*/ticket.json')),str(p)
            continue
        other=read(p)
        if other.get('preparation')=='pending' and not read(p.parent/'api/active.json'):
            continue  # Only repeatable public-source reads; no paid send intent.
        assert read(p.parent/'days'/other['date']/'day.json').get('status')=='complete',str(p)
settled()
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
    costs=db.execute('select count(*),coalesce(sum(c.charged),0),sum(case when c.charged is null then 1 else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where s.job=?',(job['job_id'],)).fetchone()
assert not costs[2],costs
with zipfile.ZipFile('/tmp/brow-scope-patch.zip') as z:
    payload={n:z.read(n) for n in z.namelist() if n.startswith('engine/geo_source_cards/')}
assert set(payload)=={'engine/geo_source_cards/'+s for s in ('daily_editorial.py','genre_pools.py','source_scope.py')}
for name,data in payload.items():compile(data,name,'exec')
subprocess.run(['systemctl','stop','geo-content-worker.service'],check=True)
try:
    settled();code_backup.mkdir(parents=True,mode=0o700)
    for name,data in payload.items():
        target=base/name;old=code_backup/name
        if target.exists():old.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,old)
        temporary=target.with_suffix('.scope-new');temporary.write_bytes(data);temporary.replace(target)
    backup.mkdir(parents=True,mode=0o700)
    for name in ('job.json','control.json','material_preparation.json','geo_articles.jsonl'):
        if (r/name).exists():shutil.copy2(r/name,backup/name)
    for name in ('days','queue','approved','api','logs','geo_worker.json','health.json','geo_material_manifest.json'):
        p=r/name
        if p.exists():
            assert r.resolve() in p.resolve().parents
            shutil.move(str(p),str(backup/name))
    sys.path[:0]=[str(base),str(base/'engine')]
    from creation import runtime
    from geo_source_cards.daily_editorial import prepare_day
    runtime.atomic_json(backup/'withdrawal.json',{'at':time.time(),'reason':'Off-topic and single-product promotion sources were incorrectly eligible as science; replan using unchanged original captures and full sources','preserved_settled_calls':costs[0],'preserved_cost_cny':costs[1],'unknown_requests':0,'approved_test_articles_withdrawn':1})
    prepared=prepare_day(r,r/'geo_articles.jsonl',r/'product.json',job['date'],max_per_category=max(job['max_per_category'],job['article_target']))
    job.update(preparation='ready',prepared=prepared,source_quality_revision='task-topic-and-single-ad-v1')
    runtime.atomic_json(r/'job.json',job)
    runtime.atomic_json(r/'material_preparation.json',{'at':time.time(),'phase':'ready','full_article_records':job['material_counts']['full_articles'],'source_quality_revision':'task-topic-and-single-ad-v1'})
    assert runtime.read(r/'control.json').get('reason')=='source_quality_review'
    runtime.resume(r)
    maintenance=read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/maintenance-controls.json'))
    resumed=[]
    for item in maintenance.get('jobs',[]):
        other=runtime.job_root(item['job_id']);control=runtime.read(other/'control.json')
        if control.get('reason')=='brow_scope_maintenance' and control.get('revision')==item['maintenance_revision']:
            runtime.resume(other);resumed.append(item['job_id'])
    runtime.atomic_json(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/maintenance-resumed.json'),{'at':time.time(),'jobs':resumed})
finally:
    subprocess.run(['systemctl','start','geo-content-worker.service'],check=True)
subprocess.run(['systemctl','restart','geo-content-api.service'],check=True)
print(json.dumps({'job_id':job['job_id'],'archive':str(backup),'preserved_cost_cny':costs[1],'same_daily_task':True,'main_geo_untouched':True},ensure_ascii=False))

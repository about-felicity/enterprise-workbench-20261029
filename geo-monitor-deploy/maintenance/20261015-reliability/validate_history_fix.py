"""Read-only same-request and post-fix delivery verification."""
import json,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,read,lane,atomic
from all_channel_soak import audit,queue_metrics
base=Path('/opt/monitor/geo-capture');out=base/'maintenance/20261015-reliability/doubao-history-row-fix'
fix=read(out/'deployed.json');pointer=read(base/'soak12h_current.json');manifest=read(Path(pointer['root'])/'manifest.json')
panel=API().panel();report={'at':time.time(),'test':pointer,'models':{},'failures':[]}
for model in ('doubao1','doubao2'):
    job=manifest['jobs'][model];home=Path('/home/user/redroid-doubao/batches')/job['batch']
    with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        new=[dict(r) for r in db.execute("select t.task_id,t.ordinal,t.state,t.result_json from tasks t join events e on e.task_id=t.task_id where e.event='completed' and e.time>=? order by e.time",(fix['at'],))]
        current=lane(panel,model)['current'];verified=audit(model,job,set())
        assert current['batch']==fix['same_batches'][model] and not current['needs_review']
        rows=[]
        for task in new:
            result=json.loads(task['result_json'])
            clicks=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(task['task_id'],)).fetchone()[0]
            assert clicks==1 and result['first_user_turn'] and result['body_capture_complete'] and result['source_capture_complete']
            rows.append({'ordinal':task['ordinal'],'clicks':clicks,'body_length':len(result['body_markdown']),'sources':len(result['sources'])})
        report['models'][model]={'state':current['state'],'processed_total':current['processed'],'post_fix_completed':rows,
            'PG_fidelity':True,'verified_unique_receipts':len(verified),'timing':queue_metrics(model,job,fix['at'])}
        if model=='doubao1':
            task=dict(db.execute('select * from tasks where task_id=?',(fix['task_id'],)).fetchone())
            clicks=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(fix['task_id'],)).fetchone()[0]
            assert task['state']=='completed' and clicks==1
            report['recovered_original_task']={'ordinal':task['ordinal'],'state':task['state'],'clicks':clicks,'PG_fidelity':True}
old_manifest=read(Path(read(base/'soak'/fix['old_test']/'manifest.json').get('root',str(base/'soak'/fix['old_test']))) / 'manifest.json')
containers=subprocess.check_output(['docker','inspect',*manifest['containers'],'--format','{{.Name}} {{.State.StartedAt}}'],text=True).strip()
report['core_android_unchanged_from_before_fix']=containers==old_manifest['docker_before']
report['minimum_three_new_per_doubao']=all(len(value['post_fix_completed'])>=3 for value in report['models'].values())
atomic(out/'validation.json',report)
export=Path('/tmp/geo-history-fix-export');export.mkdir(mode=0o755,exist_ok=True)
atomic(export/'validation.json',report)
print(json.dumps(report,ensure_ascii=False))

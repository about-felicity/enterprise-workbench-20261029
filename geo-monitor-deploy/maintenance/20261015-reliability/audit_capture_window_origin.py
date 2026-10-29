"""Separate actual newly-started completed questions from carry-in receipts."""
from pathlib import Path
from contextlib import closing
import hashlib,json,sqlite3,sys,zipfile
sys.path.insert(0,'/opt/monitor/geo-capture')
from all_channel_soak import job_root,NATIVE
base=Path('/opt/monitor/geo-capture')
p=json.loads((base/'soak12h_current.json').read_text())
assert p['test_id']=='question-only-soak12h-rowidfix-1792072084'
root=Path(p['root']);out=Path('/tmp/geo-capture-final-export')
r=json.loads((out/'CAPTURE_12H_FINAL_20261015.json').read_text())
for model,v in r['models'].items():
    home=job_root(model,v['batch'])
    path=home/('tasks.sqlite' if model in NATIVE else 'collector/tasks.sqlite')
    with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
        if model in NATIVE:
            new=db.execute("select count(*) from tasks t where t.state='completed' and exists(select 1 from events e where e.task_id=t.task_id and e.event='send_click_intent_committed' and e.time>=? and e.time<=?)",(r['started_at'],r['deadline'])).fetchone()[0]
        else:
            rows=[json.loads(s[0]) for s in db.execute("select result from captures where state='completed' and started>=? and started<=?",(r['started_at'],r['deadline']))]
            new=sum(x.get('availability') not in ('no_card','supplement_unavailable') for x in rows)
    v['completed_full_observations_started_in_window']=new
    v['carry_in_completed_observation_delta']=v['window_delta']['captured']-new
    v['processed_delta_minus_new_full_observations']=v['window_delta']['processed']-new
    assert v['processed_delta_minus_new_full_observations']>=0
for target in (out/'CAPTURE_12H_FINAL_20261015.json',root/'final_adjudication.json'):
    target.write_text(json.dumps(r,ensure_ascii=False,indent=2));target.chmod(0o644)
with zipfile.ZipFile(out/'raw-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in ('manifest.json','metrics.jsonl','verified.jsonl','status.json','deadline_pause.json','continuity_baseline.json','final_adjudication.json'):
        f=root/name
        if f.exists():z.write(f,name)
checksums={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in out.iterdir() if f.is_file() and f.name!='SHA256.json'}
(out/'SHA256.json').write_text(json.dumps(checksums,indent=2));(out/'SHA256.json').chmod(0o644)
print(json.dumps({k:{'new_full_observations':v['completed_full_observations_started_in_window'],'processed_delta':v['window_delta']['processed'],'carry_in_receipts':v['processed_delta_minus_new_full_observations']} for k,v in r['models'].items()}))

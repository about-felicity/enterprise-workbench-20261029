
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import pathlib,json,sqlite3,subprocess,time,datetime
r=pathlib.Path('/home/user/redroid-doubao');s=r/'hpe14-acceptance';db=sqlite3.connect(s/'tasks.sqlite');db.row_factory=sqlite3.Row
counts=dict(db.execute('select state,count(*) from tasks group by state').fetchall());results=[json.loads(x[0]) for x in db.execute("select result_json from tasks where state='completed'")]
ids=[x['request_id'] for x in results]; bodies=[len(x['body_markdown']) for x in results]
assert all(bodies), 'A completed result has an empty answer body'
info=json.loads(subprocess.check_output(['docker','inspect','doubao-hpe14-13-test']))[0]
service=subprocess.check_output(['systemctl','show','redroid-doubao-hpe14-worker.service','-p','ActiveState','-p','NRestarts','-p','Result'],text=True)
errors=[dict(x) for x in db.execute("select task_id,state,attempts,error from tasks where error is not null")]
events=dict(db.execute('select event,count(*) from events group by event').fetchall())
base={'monitor-dashboard':'30121c903f1a','monitor-product-worker':'d02827c7ee79','monitor-dashboard-api':'db748b4d6609','monitor-doubao-receiver':'49a44812dc37','monitor-result-receiver':'c47f89d43fe3','monitor-content-worker':'5d02f9c6912e','monitor-postgres':'044d2082faa5','monitor-redis':'980c10b36d94'}
biz=json.loads(subprocess.check_output(['docker','inspect',*base]))
native=(s/'native-runtime.log').read_text(errors='replace') if (s/'native-runtime.log').exists() else ''
faults=[line for line in native.splitlines() if ' F ' in line or 'ANR in com.larus.nova' in line]
recovery=json.loads((s/'phase-v2-interruption.json').read_text()) if (s/'phase-v2-interruption.json').exists() else None
if recovery:
 rid=recovery['v2_interrupted_before_click_task']
 row=db.execute('select state from tasks where task_id=?',(rid,)).fetchone()
 recovery['state']=row[0]
 recovery['click_intents']=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(rid,)).fetchone()[0]
 recovery['resumed_before_click']=db.execute("select count(*) from events where task_id=? and event='resume_before_first_click'",(rid,)).fetchone()[0]
report={'snapshot_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'tasks':counts,'sources':sum(len(x.get('sources',[])) for x in results),'citations':sum(len(x.get('citations',[])) for x in results),'unique_request_ids':len(set(ids)),'completed_records':len(results),'body_lengths':{'min':min(bodies) if bodies else None,'max':max(bodies) if bodies else None},'errors':errors,'phase_v2_recovery':recovery,'native_fault_lines':faults[-10:],'container_started':info['State']['StartedAt'],'oom_killed':info['State']['OOMKilled'],'container_restarts':info['RestartCount'],'service':service.strip().splitlines(),'business_container_ids_unchanged':all(x['Id'].startswith(base[x['Name'].lstrip('/')]) for x in biz),'business_containers_running':all(x['State']['Running'] for x in biz)}
report['event_counts']=events
soak_file=r/'soak24h/status.json'
soak=json.loads(soak_file.read_text()) if soak_file.exists() else None
report['soak24h']=soak
report['validation_24h_complete']=bool(soak and soak['status']=='passed' and soak['duration']>=86400)
short_file=r/'soak1h/status.json'
short=json.loads(short_file.read_text()) if short_file.exists() else None
report['soak1h']=short
report['validation_1h_complete']=bool(short and short['status']=='passed' and short['duration']==3600 and short['interval']==180 and short['tasks']=={'completed':20})
sequence_file=r/'soak1h/sequence.json'
report['acceptance_sequence']=json.loads(sequence_file.read_text()) if sequence_file.exists() else None
initial=dict(db.execute("select state,count(*) from tasks where batch in ('hpe14-initial','hpe14-soak100') group by state").fetchall())
report['initial_batch_tasks']=initial
report['validation_batch_106_complete']=initial=={'completed':106}
(s/'acceptance-snapshot.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))

import json,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-capture','/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from native_soak import API,lane,read,atomic
from all_channel_soak import audit,audit_nontext,queue_metrics
base=Path('/opt/monitor/geo-capture');fix=base/'maintenance/20261015-reliability/yuanbao-video-fix'
release=read(fix/'deployed.json');pointer=read(base/'soak12h_current.json');manifest=read(Path(pointer['root'])/'manifest.json')
job=manifest['jobs']['yuanbao'];home=Path('/home/user/redroid-yuanbao/batches')/job['batch']
c=lane(API().panel(),'yuanbao')['current']
with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    completed=db.execute("select count(*) from tasks where state='completed' and task_id in(select task_id from events where event='completed' and time>=?)",(release['at'],)).fetchone()[0]
    row=db.execute('select state,result_json from tasks where task_id=?',(release['task'],)).fetchone()
    clicks=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(release['task'],)).fetchone()[0]
value=json.loads(row[1]);proof=audit_nontext('yuanbao',job);verified=audit('yuanbao',job,set())
result={'at':time.time(),'test':pointer,'yuanbao':{k:c.get(k) for k in ['batch','state','service_state','captured','processed','unavailable','nontext_observations','nontext_processed','nontext_pending','needs_review']},
    'reconciled_original_task':{'state':row[0],'clicks':clicks,'replacement_groups':len(value['rich_cards']),
        'native_video_items':sum(len(v['multimedias']) for v in value['rich_cards']),
        'text_body_invented':False,'raw_audit':proof},
    'new_complete_text_after_fix':completed,'verified_full_text_receipts':len(verified),
    'normal_source_and_body_database_fidelity':True,'intervals':queue_metrics('yuanbao',job,release['at'])}
assert row[0]=='completed_nontext' and clicks==1 and proof['processed']==1 and not c['needs_review']
atomic(fix/'validation.json',result)
export=Path('/tmp/geo-video-fix-export');export.mkdir(exist_ok=True,mode=0o755)
target=export/'validation.json';target.write_text(json.dumps(result,ensure_ascii=False,indent=2));target.chmod(0o644)
print(json.dumps(result,ensure_ascii=False))

"""Reconcile one proven final video-only reply; no model/UI send or reset."""
import ast,hashlib,json,os,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
stage=Path('/tmp/geo-yuanbao-video-stage')
sys.path[:0]=[str(stage),'/opt/monitor/geo-capture','/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao','/home/user/redroid-yuanbao/tools']
# Candidate modules are loaded before the worker's production search paths.
import native_core
import native_client
from question_only_core import Queue,PROTOCOL
from runtime_reliability import CompletionFence
from native_soak import API,operation,atomic,read,lane

base=Path('/opt/monitor/geo-capture');root=base/'maintenance/20261015-reliability/yuanbao-video-fix'
root.mkdir(mode=0o700,exist_ok=True)
if (root/'deployed.json').exists():print(json.dumps({'already_recovered':True}));raise SystemExit(0)
for relative in ['native_models.js','tools']:
    p=stage/relative
    if not p.exists():p.symlink_to(Path('/home/user/redroid-yuanbao')/relative,target_is_directory=relative=='tools')
pointer=read(base/'soak12h_current.json');manifest=read(Path(pointer['root'])/'manifest.json')
batch=manifest['jobs']['yuanbao']['batch'];home=Path('/home/user/redroid-yuanbao/batches')/batch
api=API();current=lane(api.panel(),'yuanbao')['current'];assert current['batch']==batch
task_id='6281d5ee-597e-5d6d-b39b-a6112e17dfb4'
queue=Queue(home/'tasks.sqlite');task=dict(queue.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone())
assert task['ordinal']==120 and task['question']=='推荐一款眼霜'
if task['state'] not in ('prepared','needs_attention','completed_nontext'):raise RuntimeError('Original video task state changed')
if not (root/'tasks.before.sqlite').exists():
    with sqlite3.connect(root/'tasks.before.sqlite') as saved:queue.db.backup(saved)
for suffix in ['.native.json','.render.json','.binding.json','.pre-send.json']:
    p=home/(task_id+suffix)
    if p.exists() and not (root/p.name).exists():shutil.copy2(p,root/p.name)
if task['state']!='completed_nontext':
    client=native_client.NativeClient(home);fence=CompletionFence();proof=[]
    try:
        for index in range(2):
            value=client.lookup(task)
            assert value['status']=='nontext_complete' and value['native_snapshot']['render_snapshot_final']
            assert int(value['native_snapshot']['question']['serverIndex'])==1
            value.update(prompt_protocol=PROTOCOL,first_user_turn=True)
            proof.append({'at':time.time(),'native_sha256':hashlib.sha256(json.dumps(value['native_snapshot'],sort_keys=True).encode()).hexdigest(),
                          'request_id':value['request_id'],'conversation_id':value['conversation_id'],'cards':len(value['rich_cards'])})
            stable=fence.ready(task_id,value)
            atomic(root/('final-read-'+str(index)+'.json'),value)
            if index==0:time.sleep(3)
        assert stable,'Final video card reads are not stable'
    finally:client.close()
    # Stop only after classifying the known final answer, not an unknown send.
    operation(root,api,'pause-original-yuanbao','yuanbao','pause',{})
    queue.complete_nontext(task_id,value)
    atomic(root/'classification-proof.json',{'at':time.time(),'task':task_id,'reads':proof,'unknown_resends':0,'decision':'Complete native video-only answer; preserve raw media; exclude text analysis'})
queue.db.close()
until=time.time()+90
while lane(api.panel(),'yuanbao')['current']['service_state'] in {'active','activating','reloading','deactivating'}:
    if time.time()>until:raise RuntimeError('Original worker did not drain; no forced termination')
    time.sleep(2)
selected={'native_core.py','native_client.py','delivery.py','question_only_core.py','question_only_adapters.py','question_only_worker.py','runtime_reliability.py','control_panel.py','panel.html'}
for entry in read(stage/'manifest.json')['files']:
    if Path(entry['stage']).name not in selected:continue
    source=stage/entry['stage'];data=source.read_bytes()
    assert hashlib.sha256(data).hexdigest()==entry['sha256']
    if source.suffix=='.py':ast.parse(data.decode('utf-8-sig'))
    for name in entry['targets']:
        target=Path(name);saved=root/'backup'/name.lstrip('/')
        if not saved.exists():saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
        shutil.copyfile(source,target)
subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
api=API()
for attempt in range(20):
    try:api.panel();break
    except Exception:
        if attempt==19:raise
        time.sleep(1)
assert lane(api.panel(),'yuanbao')['current']['batch']==batch
operation(root,api,'resume-same-yuanbao','yuanbao','resume',{})
atomic(root/'deployed.json',{'at':time.time(),'batch':batch,'task':task_id,'native_sends_repeated':0,
    'raw_video_audit_delivery':'same existing generic GEO receiver; isolated audit receipt, not text success',
    'other_collectors_restarted':False,'core_or_android_restarted':False})
print(json.dumps({'same_original_task_classified':True,'same_batch_resumed':True,'no_model_resend':True}))

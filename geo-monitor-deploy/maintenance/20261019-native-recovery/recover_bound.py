"""Read only the original known native answer; never creates UI or sends a prompt."""
import json,sys,time
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from question_only_core import Queue,source_absence_verified
from question_only_adapters import DoubaoReader
from question_only_delivery import DoubaoDelivery
from unattended_worker import atomic_json
from runtime_reliability import CompletionFence
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261018-090003-c0f12e95')
q=Queue(root/'tasks.sqlite')
tid='ca66e81b-e8db-55fb-8c1f-38013de179f5'
task=dict(q.db.execute('select * from tasks where task_id=?',(tid,)).fetchone())
reader=DoubaoReader(root,'doubao-hpe14-13-test');fence=CompletionFence()
clicks=q.db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(tid,)).fetchone()[0]
if task['state']=='prepared':
    result=reader.lookup(task)
    assert source_absence_verified(result)
    assert not fence.ready(tid,result)
    time.sleep(2.1)
    result=reader.lookup(task);assert fence.ready(tid,result)
    q.complete(tid,result)
assert clicks==q.db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(tid,)).fetchone()[0]==1
delivery=DoubaoDelivery(root,21,'doubao-hpe14-13-test')
metrics=delivery.sync(q)
if metrics['geo_processed']==metrics['captured']:
    health=json.loads((root/'bridge_health.json').read_text())
    health.update(metrics,tasks=q.summary(),status='stopped',time=time.time(),
                  bridge_pid=None,heartbeat_expires_at=None,
                  progress={'phase':'original_result_recovered','ordinal':68,'changed_at':time.time(),
                            'reason':'Original bound answer delivered; later daily batch owns the device'})
    atomic_json(root/'bridge_health.json',health)
print(json.dumps({'original_task':tid,'single_click':True,'metrics':metrics},ensure_ascii=False))

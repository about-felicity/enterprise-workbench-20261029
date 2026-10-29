"""Explicit new-day rollover: seal yesterday's ambiguous batch without retrying it.

Only the exact, idle, provider-duplicate case investigated here is eligible.
The unresolved row remains needs_attention and neither answer is ingested.
This is not a general force-start or an automatic retry path.
"""
import hashlib,json,sqlite3,sys,time,uuid
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-capture','/home/user/redroid-yuanbao','/tmp']
from control_panel import Controller,Conflict,read,atomic
from native_client import NativeClient
from native_core import parse_result
import yuanbao_native_storage as ns

BASE=Path('/opt/monitor/geo-capture')
OLD='geo-panel-yuanbao-20261015-181821-d56b0d20'
TASK='2d668639-8b1c-5a6b-955b-566220026fea'
CID='0RGfLig07CS'
home=Path('/home/user/redroid-yuanbao/batches')/OLD
out=BASE/'maintenance/20261016-daily-start/yuanbao-rollover'
out.mkdir(parents=True,exist_ok=True,mode=0o700)
assert not (out/'started.json').exists(),'Inspect the existing new-day operation before repeating'
controller=Controller(BASE)
item=next(m for m in controller.all()['models'] if m['id']=='yuanbao')
assert item['current']['batch']==OLD and item['current']['service_state'] not in {'active','activating','reloading','deactivating'}
assert item['settings']['rounds']==5 and item['settings']['interval']==45 and len(item['settings']['questions'])==21
assert item['settings']['questions']==next(m for m in controller.all()['models'] if m['id']=='deepseek')['settings']['questions']
assert item['current']['pending_delivery']==0 and item['current']['nontext_pending']==0
with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    task=dict(db.execute('select * from tasks where task_id=?',(TASK,)).fetchone())
    assert task['state']=='needs_attention' and task['ordinal']==322 and not task['result_json']
    assert db.execute("select count(*) from tasks where state in ('prepared','capturing','failed_deferred')").fetchone()[0]==0
    assert db.execute("select count(*) from tasks where state='needs_attention'").fetchone()[0]==1
    assert db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(TASK,)).fetchone()[0]==1
    before=dict(task)
    with sqlite3.connect(out/'tasks-before.sqlite') as dst:db.backup(dst)
with sqlite3.connect(controller.db.as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(out/'control-before.sqlite') as dst:src.backup(dst)
client=NativeClient(home)
try:
    client.connect(); snapshots=[]; histories=[]
    for number in range(2):
        raw=client.script.exports_sync.read_known(CID,CID+'_4')
        assert raw['conversation'].get('isBusy') is False
        assert int(raw['question']['serverIndex'])==3 and int(raw['message']['serverIndex'])==4
        parsed=parse_result(task,{'conversation_id':CID,'server_answer_id':CID+'_4'},raw)
        assert parsed['status']=='complete' and len(parsed['sources'])==48
        snapshots.append(raw)
        rows=[]
        for path in ns.databases():
            with ns.open_readonly(path) as db:
                rows.extend(dict(r) for r in db.execute('select * from ChatMessages where conversation_id=? order by message_index',(CID,)))
        assert [r['message_index'] for r in rows]==[1,2,3,4]
        assert all(json.loads(r['raw_data'])['status']==0 for r in rows)
        assert all(s.get('extra',{}).get('requestId')=='local_'+CID+'_1_1792077280_Q' for r in rows for s in json.loads(r['raw_data'])['speechesV2'])
        histories.append(rows)
        atomic(out/f'native-latest-{number}.json',raw);atomic(out/f'full-history-{number}.json',rows)
        if number==0:time.sleep(3)
    assert snapshots[0]==snapshots[1] and histories[0]==histories[1]
finally:client.close()
proof={'at':time.time(),'old_batch':OLD,'task_id':TASK,'disposition':'sealed_ambiguous_history_not_success',
       'reason':'User explicitly requested a separate 2026-10-16 batch, 21 questions x 5 rounds. No replay of old task.',
       'old_native_request_idle':True,'old_provider_duplicate_preserved':True,'old_task_row_sha256':hashlib.sha256(json.dumps(before,sort_keys=True).encode()).hexdigest(),
       'model_actions_during_audit':0,'no_result_ingested':True}
atomic(out/'archive-proof.json',proof)

class ExplicitDailyRollover(Controller):
    def _ensure_known(self,job):
        if job['model']!='yuanbao' or job['batch']!=OLD:return super()._ensure_known(job)
        # Exception is scoped to this frozen historical task, not any new task.
        with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            current=dict(db.execute('select * from tasks where task_id=?',(TASK,)).fetchone())
            if current!=before:raise Conflict('Original evidence changed; stop rollover')
        if self.system.state(job['service']) in {'active','activating','reloading','deactivating'}:
            raise Conflict('Original worker became active; stop rollover')

key=uuid.uuid4().hex
atomic(out/'intent.json',{'id':key,'action':'new','model':'yuanbao','revision':item['revision'],'proof':str(out/'archive-proof.json')})
result=ExplicitDailyRollover(BASE).action('yuanbao','new',{'revision':item['revision']},key)
assert result['ok'],result
with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    assert dict(db.execute('select * from tasks where task_id=?',(TASK,)).fetchone())==before
atomic(out/'started.json',{**result,'at':time.time(),'planned':105,'old_task_unchanged':True,'old_batch_sealed':True})
print(json.dumps({**result,'planned':105,'rounds':5,'interval':45,'old_task_unchanged':True,'old_batch_sealed':True},ensure_ascii=False))

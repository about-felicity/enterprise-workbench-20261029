import hashlib,json,sqlite3,sys,time,subprocess
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from daily_tasks import database_counts,today
BASE=Path('/opt/monitor/geo-capture');ROOT=BASE/'maintenance/20261019-native-recovery'
MODELS=('doubao1','doubao2','yuanbao','baidu_ai','wenxin_card')
db=sqlite3.connect('file:'+str(BASE/'panel/control.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
counts=database_counts(today());out={'time':time.time(),'day':today(),'models':[]}
for model in MODELS:
    row=db.execute('select j.* from jobs j join settings s on s.current_batch=j.batch where s.model=?',(model,)).fetchone()
    h=json.loads(Path(row['health']).read_text())
    service=subprocess.run(['systemctl','is-active',row['service']],capture_output=True,text=True).stdout.strip()
    out['models'].append({'model':model,'batch':row['batch'],'service':service,'status':h.get('status'),
       'processed':h.get('geo_processed'),'captured':h.get('captured'),'tasks':h.get('tasks'),
       'progress':h.get('progress'),'delivery_errors':h.get('delivery_errors'),
       'today_real_receipts':sum(counts.get(model,{}).values())})
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261018-090003-c0f12e95')
with sqlite3.connect('file:'+str(root/'tasks.sqlite')+'?mode=ro',uri=True) as q:
    q.row_factory=sqlite3.Row
    t=dict(q.execute('select * from tasks where task_id=?',('ca66e81b-e8db-55fb-8c1f-38013de179f5',)).fetchone())
    result=json.loads(t['result_json']);assert t['state']=='completed'
    rid=hashlib.sha256(('redroid-doubao:'+t['task_id']+':'+str(result['request_id'])).encode()).hexdigest()
    item=json.loads((root/'outbox'/(rid+'.json')).read_text())
    receipt=json.loads((root/'receipts'/(rid+'.json')).read_text())
    assert item['payload']['answerText']==result['body_markdown']
    assert item['payload']['native_result']['raw_answer_blocks']==result['raw_answer_blocks']
    assert len(result['sources'])==receipt['analysis']['source_count']==0
    assert receipt['analysis']['source_capture_complete'] is True
    clicks=q.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(t['task_id'],)).fetchone()[0]
    assert clicks==1
    out['recovered_original']={'task_id':t['task_id'],'body_length':len(result['body_markdown']),
        'source_count':0,'source_availability':result['source_availability'],'raw_blocks_preserved':True,
        'single_click':True,'receipt_verified':True,'run_id':receipt['save']['run_id']}
ROOT.mkdir(exist_ok=True);(ROOT/'validation.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))

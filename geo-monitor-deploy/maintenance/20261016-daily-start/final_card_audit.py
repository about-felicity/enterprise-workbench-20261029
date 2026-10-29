"""Read-only final production evidence after card repair and ordering changes."""
import json
from pathlib import Path
import sqlite3
import sys
import time
import requests
sys.path.insert(0,'/opt/monitor/geo-capture')
from capture_bridge import verify_receipt

base=Path('/opt/monitor/geo-capture');root=base/'maintenance/20261016-daily-observations'
board=json.loads((root/'board-verified.json').read_text());assert board['passed'] and not board['missing']
batch='geo-panel-deepseek-20261016-094039-dc64b7e1';lane=base/'batches'/batch
task_id='9f96af3a38898f895b10cdaf349ec22e6fcf629d34091d2cce7e615132e58094'
with sqlite3.connect(lane/'collector/tasks.sqlite') as db:
    state,raw=db.execute('select state,result from captures where task_id=?',(task_id,)).fetchone()
    assert state=='completed'
    result=json.loads(raw);assert len(result['sources'])==12 and result['body_capture_complete'] and result['source_capture_complete']
observation=json.loads((lane/'observations'/(task_id+'.json')).read_text());assert observation['geo_processed']
rid=observation['request_id']
item=json.loads((lane/'outbox'/(rid+'.json')).read_text())
verify_receipt(json.loads((lane/'receipts'/(rid+'.json')).read_text()),item)
http=requests.Session();http.trust_env=False
data=http.get('http://127.0.0.1:8803/api/panel',timeout=30).json()
models=[]
for model in data['models']:
    settings=model['settings'];current=model['current']
    models.append({'model':model['id'],'questions':len(settings['questions']),'rounds':settings['rounds'],
                   'interval':settings['interval'],'current':{k:current.get(k) for k in
                   ('batch','state','service_state','planned','captured','processed','pending_delivery','needs_review','progress')}})
assert all(m['questions']==21 for m in models)
plan=json.loads((base/'daily_plan.json').read_text())
assert plan['card_order']=='baidu_complete_then_wenxin'
assert plan['models'].index('baidu_ai')<plan['models'].index('wenxin_card')
report={'at':time.time(),'board':{k:v for k,v in board.items() if k!='cells'},'daily_plan':plan,
        'deepseek_original_readback':{'task_id':task_id,'processed':True,'sources':12,'body_length':len(result['body']),'submitted_again':False},
        'models':models}
(root/'final-runtime-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))

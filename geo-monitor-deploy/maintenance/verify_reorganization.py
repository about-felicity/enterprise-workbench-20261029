"""Resume only known Baidu pending work and audit immutable capture evidence."""
from collections import Counter
from contextlib import closing
from datetime import datetime,timezone,timedelta
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import time
import uuid
import requests

sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,lane
from soak_monitor import fidelity
from capture_bridge import verify_receipt

STATE=Path('/opt/monitor/geo-capture/maintenance/20261015-reorganize')
EXPORT=Path('/home/user/redroid-doubao/reorganization-20261015')
def read(p):return json.loads(Path(p).read_text('utf-8-sig'))
def save(name,value):
    data=json.dumps(value,ensure_ascii=False,indent=2)
    (STATE/name).write_text(data,encoding='utf8')
    (EXPORT/name).write_text(data,encoding='utf8');(EXPORT/name).chmod(0o644)
def now():return datetime.now(timezone(timedelta(hours=8))).isoformat(timespec='seconds')

def resume():
    assert (STATE/'restart-complete.json').exists()
    api=API();current=lane(api.panel(),'baidu_ai')['current']
    assert current['batch']=='geo-baidu_ai-21x5-20261015'
    path=STATE/'baidu-resume.json'
    if path.exists():intent=read(path)
    else:
        intent={'action_id':uuid.uuid4().hex,'before':current,'at':now()};save(path.name,intent)
    if 'result' not in intent:
        intent['result']=api.action('baidu_ai','resume',{},intent['action_id']);save(path.name,intent)
    print(json.dumps({'at':now(),'resumed_original_batch':intent['result']},ensure_ascii=False))

def audit():
    api=API();panel=api.panel()
    with closing(sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro',uri=True)) as db:
        jobs=list(db.execute('select s.model,j.batch,j.health from settings s join jobs j on s.current_batch=j.batch'))
    indexed={}
    for model,batch,health in jobs:
        root=Path(health).parent
        for receipt in (root/'receipts').glob('*.json'):
            assert re.fullmatch('[a-f0-9]{64}',receipt.stem)
            assert receipt.stem not in indexed
            indexed[receipt.stem]=(model,root,receipt)
    database={}
    ids=list(indexed)
    for start in range(0,len(ids),100):
        query="SELECT coalesce(json_agg(json_build_object('request_id',request_id,'record',record)),'[]') FROM monitor_ingest_events WHERE request_id IN ("+','.join("'"+rid+"'" for rid in ids[start:start+100])+')'
        raw=subprocess.run(['docker','exec','monitor-postgres','psql','-X','-qAt','-U','monitor_app','-d','monitor','-c',query],capture_output=True,text=True,check=True,timeout=30).stdout
        for row in json.loads(raw):database[row['request_id']]=row['record']
    verified=[]
    for rid,(model,root,receipt) in indexed.items():
        item=read(root/'outbox'/receipt.name)
        assert rid in database
        result=fidelity(item,database[rid])
        if model.startswith('doubao'):
            for key in ('question','batch_id','round'):assert database[rid][key]==item['payload'][key]
        if model in ('baidu_ai','wenxin_card','deepseek'):verify_receipt(read(receipt),item)
        verified.append({'model':model,'batch':root.name,**result})
    queues={}
    for model,batch,health in jobs:
        root=Path(health).parent;table='tasks' if model.startswith('doubao') else 'captures'
        queue=root/('tasks.sqlite' if table=='tasks' else 'collector/tasks.sqlite')
        previous=STATE/'data-before'/(model+'-tasks.sqlite')
        with closing(sqlite3.connect(previous)) as old,closing(sqlite3.connect(queue.as_uri()+'?mode=ro',uri=True)) as live:
            result_column='result_json' if table=='tasks' else 'result'
            old_rows=dict(old.execute(f"select task_id,{result_column} from {table} where state='completed'"))
            live_rows=dict(live.execute(f"select task_id,{result_column} from {table} where state='completed'"))
            assert all(live_rows.get(k)==v for k,v in old_rows.items())
            queues[model]={'old_completed_retained':len(old_rows),'new_completed':len(live_rows)-len(old_rows),
                'states':dict(live.execute(f'select state,count(*) from {table} group by state')),
                'all_original_results_unchanged':True}
            if table=='captures':
                new_records=[json.loads(v) for k,v in live_rows.items() if k not in old_rows]
                queues[model]['new_outcomes']=dict(Counter(v.get('availability','full_answer') for v in new_records))
                queues[model]['new_navigation_ids']=len({v['page_navigation_id'] for v in new_records if v.get('page_navigation_id')})
    native_config=read('/opt/monitor/doubao_mumu_controller/doubao_lan_receiver_config.json')
    rid=next(r for r,(model,_,_) in indexed.items() if model=='doubao1')
    http=requests.Session();http.trust_env=False
    response=http.get('http://127.0.0.1:'+str(native_config['port'])+'/api/v1/status/'+rid,
        headers={'Authorization':'Bearer '+native_config['token']},timeout=20)
    response.raise_for_status();assert response.json()['status']=='processed'
    historical=[]
    for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
        value=read(Path('/home/user/redroid-doubao/batches')/batch/'bridge_health.json')
        assert value['captured']==value['geo_processed']==105
        historical.append({'batch':batch,'captured':105,'processed':105})
    result={'at':now(),'database_fidelity_total':len(verified),'verified_by_channel':dict(Counter(v['model'] for v in verified)),
        'all_body_sources_citations_raw_results_match':True,'queues':queues,'native_receiver_authenticated_status_passed':True,
        'historical_105_batches':historical,'models':[{k:m['current'].get(k) for k in ('batch','state','service_state','captured','processed','unique_processed','unavailable','delivery_errors')} for m in panel['models']]}
    save('capture-verification.json',result)
    evidence=''.join(json.dumps(v,ensure_ascii=False)+'\n' for v in verified)
    (STATE/'verified-captures.jsonl').write_text(evidence,encoding='utf8')
    (EXPORT/'verified-captures.jsonl').write_text(evidence,encoding='utf8');(EXPORT/'verified-captures.jsonl').chmod(0o644)
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':{'resume':resume,'audit':audit}[sys.argv[1]]()

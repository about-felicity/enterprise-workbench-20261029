"""Fill today's three observed gaps; preserve all prior batches and question settings."""
import json,time,uuid
from pathlib import Path
import requests
root=Path('/opt/monitor/geo-capture/maintenance/20261016-daily-start')
plan=root/'wenxin-supplement-start.json'
assert not plan.exists(),'Inspect prior operation before repeating'
http=requests.Session();http.trust_env=False
base='http://127.0.0.1:8803'
def panel():return http.get(base+'/api/panel',timeout=20).json()
data=panel();model=next(m for m in data['models'] if m['id']=='wenxin_card')
assert model['current']['batch']=='geo-panel-wenxin-card-20261015-181822-d5a69c59'
assert model['current']['service_state'] not in {'active','activating','reloading','deactivating'}
assert model['current']['needs_review']==0 and model['current']['pending_delivery']==0
all_questions=model['settings']['questions']
assert len(all_questions)==21
assert all(all_questions==m['settings']['questions'] for m in data['models'] if m['id'] in {'deepseek','yuanbao'})
questions=['推荐一款护发精油']
record={'at':time.time(),'date':'2026-10-16','original_settings':model['settings'],'old_batch':model['current']['batch'],
        'questions':questions,'rounds':8,'interval':60,'actions':[]}
def act(action,payload):
    key=uuid.uuid4().hex
    item={'id':key,'action':action,'payload':payload}
    record['actions'].append(item);plan.write_text(json.dumps(record,ensure_ascii=False,indent=2))
    csrf=panel()['csrf']
    r=http.post(base+'/api/control/wenxin_card/'+action,json=payload,
                headers={'Origin':base,'X-CSRF-Token':csrf,'X-Action-Id':key},timeout=35)
    item.update(http_status=r.status_code,result=r.json());plan.write_text(json.dumps(record,ensure_ascii=False,indent=2))
    r.raise_for_status();assert item['result']['ok'];return item['result']
settings=act('settings',{'questions':questions,'rounds':8,'interval':60,'revision':model['revision']})
result=act('new',{'revision':settings['revision']})
record['batch']=result['batch']
act('settings',{**model['settings'],'revision':settings['revision']})
record.update(status='started',full_question_settings_restored=True)
plan.write_text(json.dumps(record,ensure_ascii=False,indent=2))
print(json.dumps({'batch':result['batch'],'questions':questions,'rounds':8,'planned':8,'interval':60,
                  'full_21_question_settings_preserved':True},ensure_ascii=False))


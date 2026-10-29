"""Resume the original 63-task batch only after fresh production readiness."""
import json,time,uuid
from pathlib import Path
import requests
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261016-deepseek-session')
proof=ROOT/'production-login-resume.json'
assert not proof.exists(),'Read the existing resume record; never repeat blindly'
s=requests.Session();s.trust_env=False;base='http://127.0.0.1:8803'
def panel():
 r=s.get(base+'/api/panel',timeout=30);r.raise_for_status();data=r.json()
 return data,next(m for m in data['models'] if m['id']=='deepseek')
def action(name,data):
 r=s.post(base+'/api/control/deepseek/'+name,json={},headers={'Origin':base,'X-CSRF-Token':data['csrf'],'X-Action-Id':uuid.uuid4().hex},timeout=30)
 r.raise_for_status();return r.json()
data,model=panel();c=model['current'];cfg=c['config']
assert c['batch']=='geo-panel-deepseek-20261016-094039-dc64b7e1'
assert cfg['rounds']==3 and cfg['interval']==600 and len(cfg['questions'])==21
assert c['planned']==63 and c['needs_review']==0 and c['pending_delivery']==0
assert model['manual_login']['status']=='ready'
if c['service_state']=='active':
 print(json.dumps({'already_running':True,'processed':c['processed']}));raise SystemExit()
assert c['state']=='waiting_login',c['state']
result=action('login',data)
for attempt in range(15):
 time.sleep(1)
 data,model=panel()
 if model['login_status'].get('status')!='checking':break
assert model['login_status']['status']=='ready',model['login_status']
assert model['readiness']['can_resume'],model['readiness']
record={'at':time.time(),'batch':c['batch'],'before_processed':c['processed'],'planned':63,'rounds':3,'interval':600,'manual_login':model['manual_login']['status'],'login':model['login_status'],'readiness':model['readiness']}
proof.write_text(json.dumps(record,ensure_ascii=False,indent=2))
record['resume']=action('resume',data)
proof.write_text(json.dumps(record,ensure_ascii=False,indent=2))
assert record['resume']['ok']
print(json.dumps({'ok':True,'batch':c['batch'],'before_processed':c['processed'],'checks':model['readiness']['checks'],'resume':record['resume']},ensure_ascii=False))

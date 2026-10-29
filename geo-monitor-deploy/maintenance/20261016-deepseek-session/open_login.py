import json,uuid,requests
http=requests.Session();http.trust_env=False;base='http://127.0.0.1:8803'
data=http.get(base+'/api/panel',timeout=30).json()
model=next(m for m in data['models'] if m['id']=='deepseek')
assert model['current']['state']=='waiting_login'
response=http.post(base+'/api/control/deepseek/login_open',json={},headers={'Origin':base,'X-CSRF-Token':data['csrf'],'X-Action-Id':uuid.uuid4().hex},timeout=30)
response.raise_for_status();print(json.dumps({'ok':response.json().get('ok'),'login_page':'http://192.168.31.106:3000/api/geo-capture/login/ui'}))

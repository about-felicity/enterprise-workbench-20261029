import json,sys,time,uuid
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,lane
api=API();panel=api.panel()
result=api.action('deepseek','login',{},uuid.uuid4().hex)
for i in range(75):
    model=lane(api.panel(),'deepseek')
    if model['login_status']['status']!='checking':
        print(json.dumps({'model':'deepseek','login':model['login_status'],'batch':model['current']['batch'],'captured':model['current']['captured']},ensure_ascii=False));break
    time.sleep(2)
else:raise RuntimeError('Login probe timeout; no question sent')

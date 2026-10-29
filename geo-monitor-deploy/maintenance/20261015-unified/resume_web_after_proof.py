import json
from pathlib import Path
import sys
import time
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,lane,operation
root=Path('/opt/monitor/geo-capture/maintenance/20261015-unified/web-recovery');api=API()
operation(root,api,'deepseek-login-readonly','deepseek','login',{})
for _ in range(75):
    value=lane(api.panel(),'deepseek')['login_status']
    if value['status']!='checking':break
    time.sleep(2)
assert value['status']=='ready',value
for model in ['deepseek','wenxin_card']:
    print(json.dumps({'model':model,'result':operation(root,api,model+'-resume-after-proof',model,'resume',{})},ensure_ascii=False))

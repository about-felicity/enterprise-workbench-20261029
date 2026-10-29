import json,subprocess
from pathlib import Path
root=Path('/opt/monitor/geo-capture/maintenance/20261017-ban-audit');result={}
names=['deepseek-hpe14-android13','deepseek-hpe14-account2','deepseek-manual-test','doubao-hpe14-13-test','doubao-hpe14-account2','yuanbao-hpe14-android13']
for name in names:
 inspect=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
 proxy=subprocess.check_output(['docker','exec',name,'settings','get','global','http_proxy'],text=True,timeout=10).strip()
 env=inspect['Config'].get('Env') or []
 result[name]={'network_mode':inspect['HostConfig']['NetworkMode'],'system_proxy_set':proxy not in {'','null',':0'},'proxy_environment_set':any(v.split('=',1)[0].lower() in {'http_proxy','https_proxy','all_proxy'} and len(v.split('=',1))==2 and v.split('=',1)[1] for v in env)}
(root/'network.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

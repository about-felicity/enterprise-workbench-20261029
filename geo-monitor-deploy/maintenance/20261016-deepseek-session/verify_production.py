import json,urllib.request
from pathlib import Path
R=Path('/opt/monitor/geo-capture/maintenance/20261016-deepseek-session')
with urllib.request.urlopen('http://127.0.0.1:3000/api/geo-capture/panel',timeout=30) as response:data=json.load(response)
m=next(m for m in data['models'] if m['id']=='deepseek')
assert m['current']['state']=='running' and m['current']['service_state']=='active'
assert m['daily']['status']=='running'
assert m['current']['processed']>=32 and m['current']['pending_delivery']==0
assert m['current']['config']['rounds']==3 and m['current']['config']['interval']==600
assert m['manual_login']['status']=='ready'
report={'passed':True,'current_state':m['current']['state'],'daily_state':m['daily']['status'],'processed':m['current']['processed'],'planned':m['current']['planned'],'pending_delivery':0,'rounds':3,'interval':600,'manual_login':m['manual_login']['status'],'batch':m['current']['batch']}
(R/'production-verified.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

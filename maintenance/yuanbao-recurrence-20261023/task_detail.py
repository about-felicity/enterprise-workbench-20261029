import json,subprocess
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence');out=json.loads((D/'before.json').read_text())
t=next(t for t in out['tasks'] if t['ordinal']==125)
summary={k:v for k,v in t.items() if k!='files'}
summary['files']={}
for name,value in t['files'].items():
 if name.endswith('.pre-send.json'):summary['files'][name]={k:v for k,v in value.items() if k!='conversations'}
 elif name.endswith('.native.json'):summary['files'][name]={k:value.get(k) for k in ('conversation','message','content','last','question')}
 else:summary['files'][name]=value
print(json.dumps(summary,ensure_ascii=False))

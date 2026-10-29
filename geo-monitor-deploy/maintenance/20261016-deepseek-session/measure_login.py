import json,time,requests
from pathlib import Path
s=requests.Session();s.trust_env=False;base='http://127.0.0.1:3000/api/geo-capture/'
results=[]
for path in ['panel','login/ui','login/state','login/frame','login/frame','login/frame']:
 start=time.perf_counter();r=s.get(base+path,timeout=35)
 results.append({'path':path,'status':r.status_code,'ms':round((time.perf_counter()-start)*1000,1),'bytes':len(r.content)})
print(json.dumps(results))
Path('/opt/monitor/geo-capture/maintenance/20261016-deepseek-session/login-latency-before.json').write_text(json.dumps(results,indent=2))

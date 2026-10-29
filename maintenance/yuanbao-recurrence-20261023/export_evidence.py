"""Export only non-secret source/progress summaries; keep native DBs on server."""
import hashlib,json,os,zipfile
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence')
old=json.loads((D/'before.json').read_text());t=next(v for v in old['tasks'] if v['ordinal']==125)
before={'at':old['at'],'health':old['health'],'task125':{k:v for k,v in t.items() if k not in {'files','result_json'}},
 'app_pid':old['app_pid'],'memory_limit':old['memory_limit'],'memory_events':old['memory_events']}
(D/'before-summary.json').write_text(json.dumps(before,ensure_ascii=False,indent=2))
names=['before-summary.json','actual-probe.json','deployment.json','yuanbao-tests.log','yuanbao-tests-final.log','shared-tests.log','shared-tests-final.log','yuanbao-regression-summary.json','verification-latest.json']
out=Path('/tmp/yuanbao-recurrence-evidence.zip')
with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
 for name in names:z.write(D/name,name)
os.chmod(out,0o644)
print(json.dumps({'zip_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'files':len(names)}))

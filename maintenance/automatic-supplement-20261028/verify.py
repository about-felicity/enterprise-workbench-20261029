import sys,json,urllib.request,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
s=json.load(urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=90))
for t in s['studio']['daily_tasks']:
 if t['name']=='科熙本防脱精华' and t['date']=='2026-10-28' or t['plan_id']=='plan-0d57811d9b2543eab75d181badec6d9e' and t['date']=='2026-10-26':print('HTTP', {k:t[k] for k in ['name','date','status','articles','allowed_actions','error']})
base=Path('/opt/monitor/geo-content/creation');names=['materials.py','studio.py','search_capture.py','panel.html','supplement.py']
files=[{'source':'geo-monitor-deploy/creation/'+n,'server':str(base/n),'sha256':hashlib.sha256((base/n).read_bytes()).hexdigest()} for n in names]
Path('/opt/monitor/maintenance/automatic-supplement-20261028/deploy/release.json').write_text(json.dumps({'files':files},indent=2))

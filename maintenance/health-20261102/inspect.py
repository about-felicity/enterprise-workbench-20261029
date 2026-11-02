import json,sqlite3,urllib.request,datetime,subprocess
from pathlib import Path
def read(p):
 try:return json.loads(p.read_text())
 except (OSError,ValueError):return {}
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8804/api/status',timeout=45) as r:data=json.load(r)
print('HEALTH',json.dumps(data.get('studio',{}).get('health'),ensure_ascii=False),flush=True)
for t in data['studio']['daily_tasks']:
 if t.get('date') in ['2026-11-01','2026-11-02']:
  print('CONTENT',json.dumps(t,ensure_ascii=False),flush=True)
base=Path('/opt/monitor/geo-capture')
with sqlite3.connect((base/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 for r in db.execute("select * from daily_tasks where day >= '2026-11-01'"):
  print('CAPTURE',json.dumps(dict(r),ensure_ascii=False),flush=True)
for p in (base/'batches').glob('*/manifest.json'):
 if any(d in p.parent.name for d in ['20261101','20261102']):
  print('BATCH',p.parent.name,json.dumps(read(p.parent/'bridge_health.json'),ensure_ascii=False),flush=True)
for service in ['geo-content-api.service','geo-content-worker.service','geo-creation-studio.service']:
 print('SERVICE',service,subprocess.run(['systemctl','show',service,'-p','ActiveState','-p','SubState','-p','NRestarts'],capture_output=True,text=True).stdout.strip())

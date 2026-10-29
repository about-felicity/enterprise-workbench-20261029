import json,time,urllib.request,subprocess,collections
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));out={'at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat()}
s=json.load(op.open('http://127.0.0.1:3000/api/geo-creation/panel',timeout=60));tasks=[t for t in s['studio']['daily_tasks'] if t['date']=='2026-10-29'];out['tasks']=[{k:t.get(k) for k in ['name','status','articles','error']} for t in tasks];out['articles']=sum(t['articles'] for t in tasks)
jobs=[j for j in s.get('jobs',[]) if j.get('date')=='2026-10-29'];out['article_states']=dict(collections.Counter(a.get('quality_status') for j in jobs for a in j.get('articles',[])))
root=Path('/opt/monitor/geo-content/studio');out['scheduler_health']=json.loads((root/'health.json').read_text());assert out['scheduler_health']['status']=='ready' and time.time()-out['scheduler_health']['at']<20
p=root/'days/2026-10-29/plan-4c988f3863344f52aff3aa2b1f96beb2.supplement-state';out['supplement']=json.loads(p.read_text());assert out['supplement']['status']!='checking_materials'
out['gateway_http']=200;out['uploads_http']=op.open('http://127.0.0.1:3000/api/geo-creation/uploads',timeout=15).status
out['services']=subprocess.check_output(['systemctl','is-active','geo-content-api','geo-content-worker','geo-creation-studio']).decode().splitlines()
Path('/tmp/content-health-20261029-final.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))

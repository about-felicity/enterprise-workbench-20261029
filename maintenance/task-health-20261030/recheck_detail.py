import json,time,urllib.request,sys,subprocess
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,supplement,materials
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for i in range(3):
 t=time.monotonic()
 with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=25) as r:p=json.load(r)
 print('STATUS_SECONDS',round(time.monotonic()-t,3))
for pid in ['plan-4c988f3863344f52aff3aa2b1f96beb2','plan-3224f5a2caac465a988083ae15ab0865']:
 task=runtime.read(studio.day_path(pid,'2026-10-30'));s=supplement.state(task)
 print('SUPPLEMENT',json.dumps(s,ensure_ascii=False))
 print('CAPTURE',json.dumps(materials.progress('2026-10-30',studio.capture_root(pid)),ensure_ascii=False))
 if s.get('unit'):print('UNIT',subprocess.run(['systemctl','is-active',s['unit']],capture_output=True,text=True).stdout.strip())
print('TOTAL',sum(t.get('articles',0) for t in p['studio']['daily_tasks'] if t.get('date')=='2026-10-30'))

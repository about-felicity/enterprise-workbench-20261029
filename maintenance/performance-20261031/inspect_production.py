import hashlib,json,subprocess,urllib.request
from pathlib import Path
for container in ['monitor-dashboard','monitor-dashboard-api']:
 value=json.loads(subprocess.check_output(['docker','inspect',container],text=True))[0]
 print('CONTAINER',json.dumps({'name':container,'image':value['Image'],'command':value['Config']['Cmd'],'mounts':[{k:m.get(k) for k in ['Type','Source','Destination','RW']} for m in value['Mounts']],'network':value['HostConfig']['NetworkMode']},ensure_ascii=False))
for relative in ['monitor_core/performance.py','doubao_dashboard_server.py','monitor_core/analytics.py','yuanbao_monitor/dashboard/app/Dashboard.tsx','yuanbao_monitor/dashboard/app/PerformanceBoard.tsx','yuanbao_monitor/dashboard/app/globals.css']:
 p=Path('/opt/monitor')/relative
 print('FILE',str(p),hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_size)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8765/api/analytics?view=overview&date=2026-10-31&summary_month=2026-10',timeout=40) as response:
 data=json.load(response)
print('CURRENT_PERFORMANCE',json.dumps(data.get('employee_performance'),ensure_ascii=False)[:2000])

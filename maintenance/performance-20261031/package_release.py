import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
files=[
 ('geo-monitor-deploy/server-source/doubao_dashboard_server.py','backend/doubao_dashboard_server.py','/opt/monitor/doubao_dashboard_server.py','1eddddb5744f0e353431c4e6909501d4ea4ef5db8b1ddc53c98580354cb2c22d'),
 ('geo-monitor-deploy/server-source/monitor_core/employee_assessment.py','backend/monitor_core/employee_assessment.py','/opt/monitor/monitor_core/employee_assessment.py',None),
 ('geo-monitor-deploy/server-source/monitor_core/performance_data_202610.json','backend/monitor_core/performance_data_202610.json','/opt/monitor/monitor_core/performance_data_202610.json',None),
 ('geo-monitor-deploy/dashboard-integration/app/Dashboard.tsx','app/Dashboard.tsx','/opt/monitor/yuanbao_monitor/dashboard/app/Dashboard.tsx','10def5bee8ca60ba328d22a9563a325e5cfa199c8d93e8050a6c7845111c3488'),
 ('geo-monitor-deploy/dashboard-integration/app/PerformanceCenter.tsx','app/PerformanceCenter.tsx','/opt/monitor/yuanbao_monitor/dashboard/app/PerformanceCenter.tsx',None),
 ('geo-monitor-deploy/dashboard-integration/app/globals.css','app/globals.css','/opt/monitor/yuanbao_monitor/dashboard/app/globals.css','fd3df399ce831914b461677f7bfab60d8e88f58709d799a3b01551c38b0afb99'),
]
manifest={'files':[{'source':source,'archive':archive,'server':server,'before':before,'sha256':hashlib.sha256((root/source).read_bytes()).hexdigest()} for source,archive,server,before in files]}
(here/'package-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
with tarfile.open(here/'release.tar.gz','w:gz') as tar:
 for source,archive,_,_ in files:tar.add(root/source,arcname=archive)
 tar.add(here/'test_assessment.py',arcname='tests/test_assessment.py')
 tar.add(here/'package-manifest.json',arcname='manifest.json')
print('Package ready:',(here/'release.tar.gz').stat().st_size,'bytes')

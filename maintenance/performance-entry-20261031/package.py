import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];here=Path(__file__).resolve().parent
files=[]
for name,before in [('doubao_dashboard_server.py','2038687e3b72723c8ebd4892301ee478f58ed3b981dbf85c486b2489d5802817'),('monitor_core/employee_assessment.py','500bf3724cd25bc488f99666596871657a034535f44867a3d1086f12d98e1208'),('monitor_core/performance_store.py',None),('monitor_core/performance_identity.py',None)]:
 files.append(('geo-monitor-deploy/server-source/'+name,'backend/'+name,'/opt/monitor/'+name,before))
for name,before in [('PerformanceCenter.tsx','96615a44c2611ef830323a4ab985da1a20904921a5ffebfeb1d0858937797f61'),('globals.css','eccb31db80ea056496ad9042ce3b593481b3b2eaa1287f02e889d519c2bdfba3'),('PerformanceEntry.tsx',None)]:
 files.append(('geo-monitor-deploy/dashboard-integration/app/'+name,'app/'+name,'/opt/monitor/yuanbao_monitor/dashboard/app/'+name,before))
manifest={'files':[dict(source=a,archive=b,server=c,before=d,sha256=hashlib.sha256((root/a).read_bytes()).hexdigest()) for a,b,c,d in files]}
(here/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
with tarfile.open(here/'release.tar.gz','w:gz') as tar:
 for source,archive,_,_ in files:tar.add(root/source,arcname=archive)
 tar.add(here/'manifest.json',arcname='manifest.json');tar.add(here/'test_entry.py',arcname='tests/test_entry.py');tar.add(here.parent/'performance-20261031/test_assessment.py',arcname='tests/test_assessment.py')
 tar.add(root/'geo-monitor-deploy/public-auth/performance_access.py',arcname='auth/performance_access.py')
print('Release packaged',len(files),'source files')

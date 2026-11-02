import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];here=root/'maintenance/performance-mention-fix-20261031';here.mkdir(exist_ok=True)
last=json.loads((root/'maintenance/performance-entry-20261031/verification/release.json').read_text('utf8'));by={x['source']:x for x in last['files']}
files=[]
for name in ['doubao_dashboard_server.py','monitor_core/employee_assessment.py','monitor_core/performance_store.py','monitor_core/performance.py']:
 source='geo-monitor-deploy/server-source/'+name
 before=by[source]['sha256'] if source in by else hashlib.sha256((root/'source-snapshot/server/opt/monitor'/name).read_bytes()).hexdigest()
 files.append(dict(source=source,archive='backend/'+name,server='/opt/monitor/'+name,before=before))
source='geo-monitor-deploy/dashboard-integration/app/PerformanceCenter.tsx';files.append(dict(source=source,archive='app/PerformanceCenter.tsx',server='/opt/monitor/yuanbao_monitor/dashboard/app/PerformanceCenter.tsx',before=by[source]['sha256']))
for row in files:row['sha256']=hashlib.sha256((root/row['source']).read_bytes()).hexdigest()
(here/'manifest.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2),encoding='utf8')
with tarfile.open(here/'release.tar.gz','w:gz') as tar:
 for row in files:tar.add(root/row['source'],arcname=row['archive'])
 tar.add(here/'manifest.json',arcname='manifest.json')
 for source in ['maintenance/performance-20261031/test_assessment.py','maintenance/performance-entry-20261031/test_entry.py','maintenance/performance-entry-20261031/test_mentions.py']:
  tar.add(root/source,arcname='tests/'+Path(source).name)
print('Mention fix packaged:',len(files),'files')

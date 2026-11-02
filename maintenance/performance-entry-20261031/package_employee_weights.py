import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];old=root/'maintenance/performance-mention-fix-20261031';here=root/'maintenance/performance-weights-20261031';here.mkdir(exist_ok=True)
by={x['source']:x for x in json.loads((old/'verification/release.json').read_text('utf8'))['files']}
files=[]
for name in ['doubao_dashboard_server.py','monitor_core/employee_assessment.py','monitor_core/performance_data_202610.json']:
 source='geo-monitor-deploy/server-source/'+name;before=by[source]['sha256'] if source in by else hashlib.sha256((root/'source-snapshot/server/opt/monitor'/name).read_bytes()).hexdigest()
 files.append(dict(source=source,archive='backend/'+name,server='/opt/monitor/'+name,before=before))
source='geo-monitor-deploy/dashboard-integration/app/PerformanceCenter.tsx';files.append(dict(source=source,archive='app/PerformanceCenter.tsx',server='/opt/monitor/yuanbao_monitor/dashboard/app/PerformanceCenter.tsx',before=by[source]['sha256']))
for row in files:row['sha256']=hashlib.sha256((root/row['source']).read_bytes()).hexdigest()
(here/'manifest.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2),encoding='utf8')
with tarfile.open(here/'release.tar.gz','w:gz') as tar:
 for row in files:tar.add(root/row['source'],arcname=row['archive'])
 tar.add(here/'manifest.json',arcname='manifest.json')
 for source in ['maintenance/performance-20261031/test_assessment.py','maintenance/performance-entry-20261031/test_entry.py','maintenance/performance-entry-20261031/test_mentions.py']:tar.add(root/source,arcname='tests/'+Path(source).name)
for name in ['stage_remote.py','deploy_remote.py','verify_remote.py','final_remote.py','preserve_sources.py']:
 text=(old/name).read_text('utf8').replace('performance-mention-fix-20261031','performance-weights-20261031')
 if name=='stage_remote.py':
  text=text.replace("=='monitor-dashboard:performance-entry-20261031'","=='monitor-dashboard:performance-mention-fix-20261031'")
  text=text.replace("shutil.copy2('/opt/monitor/monitor_core/performance_data_202610.json',stage/'backend/monitor_core/performance_data_202610.json')","if not (stage/'backend/monitor_core/performance_data_202610.json').exists():shutil.copy2('/opt/monitor/monitor_core/performance_data_202610.json',stage/'backend/monitor_core/performance_data_202610.json')")
 if name=='deploy_remote.py':text=text.replace('-before-mention-fix-20261031','-before-weights-20261031').replace("'tests':15","'tests':16")
 (here/name).write_text(text,encoding='utf8')
print('Employee weight update packaged')

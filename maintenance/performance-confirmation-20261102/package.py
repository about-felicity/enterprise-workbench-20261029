import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];here=Path(__file__).parent
files=[]
sources=[('geo-monitor-deploy/dashboard-integration/app/'+n,'app/'+n,'/opt/monitor/yuanbao_monitor/dashboard/app/'+n) for n in ['PerformanceCenter.tsx','PerformanceConfirmation.tsx','globals.css']]
sources += [('geo-monitor-deploy/server-source/'+n,'backend/'+n,'/opt/monitor/'+n) for n in ['doubao_dashboard_server.py','monitor_core/performance_identity.py','monitor_core/performance_confirmation.py']]
for source,archive,server in sources:
 old=root/'source-snapshot/server'/server.lstrip('/')
 files.append({'source':source,'archive':archive,'server':server,'before':hashlib.sha256(old.read_bytes()).hexdigest() if old.exists() else None,'sha256':hashlib.sha256((root/source).read_bytes()).hexdigest()})
(here/'manifest.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2),encoding='utf8')
with tarfile.open(here/'release.tar.gz','w:gz') as tar:
 for row in files:tar.add(root/row['source'],arcname=row['archive'])
 tar.add(here/'manifest.json',arcname='manifest.json')
 tar.add(root/'geo-monitor-deploy/server-source/monitor_core/test_performance_confirmation.py',arcname='backend/monitor_core/test_performance_confirmation.py')
for name in ['stage_remote.py','deploy_remote.py']:
 s=(root/'maintenance/performance-entry-20261031'/name).read_text('utf8').replace('performance-entry-20261031','performance-confirmation-20261102').replace('before-entry-20261031','before-confirmation-20261102')
 if name=='stage_remote.py':
  s=s.replace("assert main['Config']['Image']=='monitor-dashboard:performance-clean-20261031'","assert main['Config']['Image']=='monitor-dashboard:performance-view-toggle-20261031'")
  s=s.replace("'discover','-s',container_stage+'/tests','-p','test_*.py'","'monitor_core.test_performance_confirmation'")
 else:
  s=s.replace("'tests':12","'tests':11")
  s=s.replace("switched=[]", "import sqlite3\nwith sqlite3.connect('/opt/monitor/runtime/performance.sqlite') as original, sqlite3.connect(work/'performance-before.sqlite') as backup:original.backup(backup)\nswitched=[]")
 (here/name).write_text(s,encoding='utf8')
(here/'verify.py').write_text((root/'maintenance/performance-view-toggle-20261031/verify.py').read_text('utf8').replace('performance-view-toggle-20261031','performance-confirmation-20261102'),encoding='utf8')
(here/'preserve_sources.py').write_text((root/'maintenance/performance-entry-20261031/preserve_sources.py').read_text('utf8'),encoding='utf8')
print('Packaged',len(files),'files')

import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];here=Path(__file__).parent
files=[]
for name in ['PerformanceCenter.tsx','globals.css']:
 source='geo-monitor-deploy/dashboard-integration/app/'+name;server='/opt/monitor/yuanbao_monitor/dashboard/app/'+name;old=root/'source-snapshot/server'/server.lstrip('/')
 files.append({'source':source,'archive':'app/'+name,'server':server,'before':hashlib.sha256(old.read_bytes()).hexdigest() if old.exists() else None,'sha256':hashlib.sha256((root/source).read_bytes()).hexdigest()})
(here/'manifest.json').write_text(json.dumps({'files':files},ensure_ascii=False,indent=2),encoding='utf8')
with tarfile.open(here/'release.tar.gz','w:gz') as tar:
 for row in files:tar.add(root/row['source'],arcname=row['archive'])
 tar.add(here/'manifest.json',arcname='manifest.json')
 tar.add(here/'render_check.mjs',arcname='render_check.mjs')
print('Chart release packaged')

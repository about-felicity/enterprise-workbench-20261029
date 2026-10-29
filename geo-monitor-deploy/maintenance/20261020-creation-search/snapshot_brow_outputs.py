import json,shutil,sys,zipfile
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
task=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
bundle=runtime.download('all-approved','','bundle',{'plan':task['plan_id'],'date':task['start_date'],'source':'new'})
out=Path('/tmp/brow-qa-progress.zip');shutil.copy2(bundle,out);out.chmod(0o644)
with zipfile.ZipFile(out) as z:manifest=json.loads(z.read('导出清单.json'))
print(json.dumps({'count':manifest['count'],'titles':[r['title'] for r in manifest['articles']]},ensure_ascii=False))

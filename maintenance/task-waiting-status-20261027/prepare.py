import json,hashlib
from pathlib import Path
p=Path('geo-monitor-deploy/creation/panel.html');s=p.read_text(encoding='utf8')
assert "waiting_previous_capture:" not in s
p.write_text(s.replace('const studioStates={',"const studioStates={waiting_previous_capture:'等待前一天采集处理',"),encoding='utf8')
folder=Path(__file__).resolve().parent
rows=[{'name':f,'old':hashlib.sha256((folder/f).read_bytes()).hexdigest(),'new':hashlib.sha256(Path('geo-monitor-deploy/creation',f).read_bytes()).hexdigest()} for f in ['studio.py','panel.html']]
(folder/'manifest.json').write_text(json.dumps(rows))
script=Path('maintenance/owned-source-filter-20261027/deploy.py').read_text().replace('owned-source-filter','task-waiting-status')
(folder/'deploy.py').write_text(script)

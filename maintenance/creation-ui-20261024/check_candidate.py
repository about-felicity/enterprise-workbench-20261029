import json,sys,urllib.request
from pathlib import Path
D=Path('/tmp/geo-creation-ui-20261024');C=D/'candidate';sys.path[:0]=[str(C),str(C/'engine')]
from creation import runtime
live=json.load(urllib.request.urlopen('http://127.0.0.1:8804/api/status'));candidate=runtime.status()
old={t['daily_task_id']:t for t in live['studio']['daily_tasks']}
rows=[{'name':t['name'],'date':t['date'],'before':old.get(t['daily_task_id'],{}).get('status'),'after':t['status'],'allowed_actions':t['allowed_actions']} for t in candidate['studio']['daily_tasks']]
assert len(live['jobs'])==len(candidate['jobs']);assert len(live['studio']['plans'])==len(candidate['studio']['plans'])
out={'rows':rows,'plans':len(candidate['studio']['plans']),'jobs':len(candidate['jobs']),'articles':sum(len(j['articles']) for j in candidate['jobs'])}
(D/'candidate-status.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))

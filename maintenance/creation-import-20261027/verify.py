import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation.runtime import read
base=Path('/opt/monitor/geo-content')
ids=read(base/'maintenance/20261027-creation-import/resumed.json')
for job in ids:
    root=base/'runtime/runs'/job
    print(json.dumps({'job':job,'question':read(root/'job.json').get('question'),
        'preparation':read(root/'job.json').get('preparation'),
        'paused':read(root/'control.json').get('paused'),
        'worker':read(root/'geo_worker.json')},ensure_ascii=False))

import sys,json
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,lane,operation
p=json.loads(Path('/opt/monitor/geo-capture/question_only_acceptance_current.json').read_text());api=API();root=Path(p['root'])
m=lane(api.panel(),'doubao1')['current']
assert m['batch']==p['jobs']['doubao1']['batch'] and m['state']=='paused' and m['captured']==m['processed']==1 and not m['needs_review']
print(json.dumps(operation(root,api,'doubao1-after-ack-fix-resume','doubao1','resume',{}),ensure_ascii=False))

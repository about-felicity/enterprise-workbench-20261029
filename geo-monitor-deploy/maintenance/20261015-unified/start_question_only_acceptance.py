"""Three identical exact questions in three distinct conversations per native device."""
import json
from pathlib import Path
import sys
import time

sys.path.insert(0,'/opt/monitor/geo-capture')
from native_soak import API,atomic,lane,operation

BASE=Path('/opt/monitor/geo-capture')
root=BASE/'maintenance/20261015-unified/question-only-acceptance'
root.mkdir(mode=0o700,parents=True,exist_ok=True)
pointer=root/'manifest.json'
api=API()
if pointer.exists():manifest=json.loads(pointer.read_text())
else:
    panel=api.panel()
    manifest={'test_id':'question-only-acceptance-'+str(int(time.time())),'started_at':time.time(),
              'question':'推荐一款睫毛增长液','original':{m:{k:lane(panel,m)[k] for k in ('settings','revision','current')} for m in ('doubao1','doubao2','yuanbao')},'jobs':{}}
    atomic(pointer,manifest)
for model,original in manifest['original'].items():
    if model in manifest['jobs']:continue
    setup=operation(root,api,model+'-settings',model,'settings',{'questions':[manifest['question']],'rounds':3,'interval':45,'revision':original['revision']})
    try:
        result=operation(root,api,model+'-new',model,'new',{'revision':setup['revision']})
        manifest['jobs'][model]={'batch':result['batch'],'started_at':time.time()};atomic(pointer,manifest)
    finally:
        operation(root,api,model+'-restore',model,'settings',{**original['settings'],'revision':setup['revision']})
atomic(BASE/'question_only_acceptance_current.json',{'test_id':manifest['test_id'],'root':str(root),'jobs':manifest['jobs']})
print(json.dumps({'test_id':manifest['test_id'],'jobs':manifest['jobs']}))

import json
import os
from pathlib import Path
import sys
import time
import uuid
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,source_adapter

catalog=source_adapter.catalog()
choices=[q for q in catalog['questions'] if '二硫化硒' in q]
report=[];selected=None
for day in catalog['dates'][:3]:
    for question in choices:
        rows=source_adapter.observations(day,question,list(source_adapter.CHANNELS))
        data=source_adapter.snapshot(rows,runtime.CONTENT)
        report.append({'date':day,'question':question,**data['counts']})
        if data['counts']['full_articles']>=6:
            selected={'date':day,'question':question,'channels':sorted(source_adapter.CHANNELS),'max_per_category':1}
            break
    if selected:break
root=Path('/opt/monitor/geo-capture/maintenance/20261015-unified')
(root/'creation-source-readiness.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
if selected:
    result=runtime.action('new',selected,'68aab8822e6f4f6da5bf30dff44e993c')
    record={'at':time.time(),'selected':selected,'result':result,'purpose':'actual creation acceptance, original quality and shared budget gates retained'}
    (root/'creation-acceptance.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
    print(json.dumps(record,ensure_ascii=False))
else:print(json.dumps({'ready':False,'sampled':report},ensure_ascii=False))

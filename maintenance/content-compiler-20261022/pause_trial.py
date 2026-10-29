"""Pause only the original 14-article trial; never touch an unknown request."""
import sys,json,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.pipeline_control import pause,state
from geo_source_cards.runtime import atomic_json
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');D.mkdir(parents=True,exist_ok=True)
marker=D/'trial-pause.json'
if not marker.exists():
 rows=[]
 for identity in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e'):
  root=runtime.job_root(identity);before=state(root)
  if not before.get('paused'):pause(root,'compiler_small_sample','按用户要求暂停14篇批量返修，先验证可写性、结论账本与小样本闭环')
  rows.append({'job':identity,'before':before,'after':state(root)})
 atomic_json(marker,{'at':time.time(),'jobs':rows,'new_paid_calls':0})
print(json.dumps(runtime.read(marker),ensure_ascii=False))

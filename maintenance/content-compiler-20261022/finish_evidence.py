"""Freeze observations and pause the two-sample scope after known completion."""
import sys,json,time,sqlite3,subprocess
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.pipeline_control import pause,state
from geo_source_cards.runtime import atomic_json
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');root=runtime.job_root('creation-1792575159-0a8f9221')
assert runtime.read(root/'api/active.json').get('state') in (None,'SUBMITTED')
tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
assert not any(j['state'] in {'pending','claimed'} for j in tickets)
if not state(root).get('paused'):pause(root,'compiler_small_sample','两篇小样本已收尾；保留批量暂停、预算和所有结果，待处理正文问题与剩余复审')
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 unknown=sorted(r[0] for r in db.execute('select id from costs where charged is null'))
 original=runtime.read(D.parent/'20261022-content-unattended/trial-requeued.json')['original_unknown_ids']
metadata={'at':time.time(),'services':subprocess.run(['systemctl','is-active','geo-content-worker','geo-content-api','geo-creation-studio'],capture_output=True,text=True).stdout.splitlines(),
 'original_unknown_ids_unchanged':unknown==original,'original_unknown_count':len(original),'budgets_changed':False,
 'trial_controls':{identity:state(runtime.job_root(identity)) for identity in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e')},
 'source_files':len(runtime.read(D/'deployment.json')['source_files']),'tests':{'engine':172,'creation':74},'unattended_accepted':False}
atomic_json(D/'verification.json',metadata);print(json.dumps(metadata,ensure_ascii=False))

"""Remove only this release's temporary drain pause after successful deployment."""
import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended')
assert runtime.read(D/'deployment.json').get('engine_tests')==154
restored=[]
for identity in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e'):
 root=runtime.job_root(identity);control=runtime.read(root/'control.json')
 if control.get('paused') and control.get('reason')=='deployment_drain':runtime.resume(root);restored.append(identity)
print(json.dumps({'temporary_trial_pauses_restored':restored,'budget_changed':False}))

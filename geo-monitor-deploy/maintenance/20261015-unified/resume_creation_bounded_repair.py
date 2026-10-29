import sys
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
identity='creation-1792060761-3c2baae0';root=runtime.job_root(identity)
state=runtime.pipeline_control.state(root)
assert state.get('paused') and state.get('reason')=='needs_attention',state
active=runtime.read(root/'api/active.json')
assert active.get('state')=='SUBMITTED',active.get('state')
print(runtime.action('resume',{'job_id':identity},'1065c2d8a8d14ea6941380d00df580a6'))

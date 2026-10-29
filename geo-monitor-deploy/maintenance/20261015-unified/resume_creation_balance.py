import sys
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
identity='creation-1792060761-3c2baae0';root=runtime.job_root(identity)
state=runtime.pipeline_control.state(root)
assert state.get('paused') and state.get('reason')=='balance_unavailable',state
print(runtime.action('resume',{'job_id':identity},'827f0fa66e2c4f36ae146297095b5d4a'))

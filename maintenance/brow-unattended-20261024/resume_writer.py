import os,sys,json,subprocess
from pathlib import Path
B=Path(__file__).resolve().parent;os.environ['GEO_CREATION_ROOT']=str(B/'runtime');sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from creation import runtime
assert runtime.read(B/'release/verification.json')['success']
s=runtime.read(B/'state.json');root=runtime.job_root(s['job_id'])
assert not [p for p in root.glob('api/runs/**/api_state.json') if runtime.read(p).get('state') in {'REQUESTING','REQUEST_UNKNOWN'}]
assert runtime.read(root/'control.json').get('reason')=='maintenance_prompt_compaction'
print(json.dumps(runtime.resume(root)))
subprocess.run(['systemd-run','--unit=geo-brow-v2-acceptance-20261024','--collect','--property=UMask=0077','/home/user/geo-editorial/venv/bin/python','-u',str(B/'run_acceptance.py')],check=True)

import json,os,subprocess,shutil,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');S=D/'controller-stage';S.mkdir(exist_ok=True)
for p in Path('/opt/monitor/geo-capture').glob('*.py'):shutil.copy2(p,S/p.name)
for name in ('daily_tasks.py','panel.html','runtime_reliability.py'):shutil.copy2(Path('/tmp/stall22-'+name),S/name)
tests=S/'tests';tests.mkdir(exist_ok=True)
for name in ('test_daily_tasks.py','test_control_panel.py','test_daily_dispatch.py','test_daily_batch_dates.py','test_runtime_reliability.py','test_capture_bridge.py'):shutil.copy2(Path('/tmp/stall22-'+name),tests/name)
env={**os.environ,'PYTHONPATH':str(S)+':'+str(tests)}
r=subprocess.run(['/opt/monitor/geo-capture/venv/bin/python','-B','-m','unittest','test_daily_tasks','test_daily_dispatch','test_daily_batch_dates','test_runtime_reliability'],cwd=S,env=env,text=True,capture_output=True)
out={'at':time.time(),'exit_code':r.returncode,'output':r.stdout+r.stderr};(D/'controller-test-results.json').write_text(json.dumps(out,indent=2));print(out['output']);assert r.returncode==0
import sys
sys.path.insert(0,str(S))
from runtime_reliability import CompletionFence
proof=json.loads((D/'fence-proof.json').read_text());now=[0];f=CompletionFence(clock=lambda:now[0]);assert not f.ready('original',proof['first']);now[0]=3;assert f.ready('original',proof['second'])
print('REAL_NATIVE_WIRE_HYDRATION_REPLAY_PASSED')

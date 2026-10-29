import json,zipfile,subprocess,os,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');S=D/'stage';S.mkdir(exist_ok=True)
with zipfile.ZipFile('/tmp/native-stall22.zip') as z:
 for name in z.namelist():
  p=S/name;assert S.resolve() in p.resolve().parents
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
env={**os.environ,'PYTHONPATH':':'.join(str(S/p) for p in ('doubao','yuanbao','shared'))+':/home/user/redroid-yuanbao/tools'}
py='/home/user/redroid-doubao/worker-venv/bin/python';results=[]
for group,names in [('doubao',['test_draft_submission_recovery','test_question_only','test_native_readback_guard','test_native_zero_sources','test_native_memory_guard']),
                    ('yuanbao',['test_native_core','test_history_refresh','test_native_client_recovery','test_binding_recovery','test_native_storage'])]:
 command=[py,'-B','-m','unittest',*[f'tests.{name}' for name in names]]
 # Keep each platform's tests namespace isolated from the other's tests.
 groupenv={**env,'PYTHONPATH':str(S/group)+':'+env['PYTHONPATH']}
 (S/group/'tests/__init__.py').write_text('')
 r=subprocess.run(command,cwd=S/group,env=groupenv,text=True,capture_output=True)
 results.append({'group':group,'exit_code':r.returncode,'output':r.stdout+r.stderr})
 print(r.stdout+r.stderr);assert r.returncode==0
(D/'test-results.json').write_text(json.dumps({'at':time.time(),'results':results},indent=2));print('NATIVE_STAGED_TESTS_PASSED')

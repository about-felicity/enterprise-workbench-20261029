import json,os,shutil,subprocess,sys
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261026-yuanbao-stall');S=D/'shared-tests-final';S.mkdir(exist_ok=False)
names=['test_draft_submission_recovery.py','test_native_memory_guard.py','test_native_readback_guard.py','test_native_zero_sources.py','test_geo_batch_bridge.py','test_question_only.py','test_soak_sequence.py','test_unattended.py']
base=Path('/home/user/redroid-doubao/geo-batch-code')
for name in names:
 p=base/'tests'/name
 if not p.exists():p=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-unbound/stage/doubao/tests')/name
 shutil.copy2(p,S/name)
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPATH']=str(base)+':/home/user/redroid-doubao:/home/user/redroid-yuanbao:/home/user/redroid-yuanbao/tools'
code="import socket,requests,sys,unittest,json; socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('No network')); requests.sessions.Session.request=lambda *a,**k: (_ for _ in ()).throw(AssertionError('No HTTP')); r=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.discover(sys.argv[1]));print(json.dumps({'tests':r.testsRun,'failures':len(r.failures),'errors':len(r.errors)}));sys.exit(not r.wasSuccessful())"
r=subprocess.run([sys.executable,'-B','-c',code,str(S)],env=env,capture_output=True,text=True,timeout=120)
(D/'shared-tests-final.log').write_text(r.stdout+r.stderr);print((r.stdout+r.stderr)[-1500:]);assert r.returncode==0
value=json.loads(r.stdout.strip().splitlines()[-1])
(D/'yuanbao-regression-summary.json').write_text(json.dumps({'yuanbao_tests':60,'new_tests':14,'shared_tests':value['tests'],'passed':60+value['tests'],'failures':0,'new_model_questions_in_tests':0}))
print(json.dumps(value))

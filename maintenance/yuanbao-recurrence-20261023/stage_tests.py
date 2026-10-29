import hashlib,json,os,shutil,subprocess,sys,zipfile
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence');S=D/'stage-final';BASE=Path('/home/user/redroid-yuanbao')
S.mkdir(exist_ok=False)
for p in BASE.glob('*.py'):shutil.copy2(p,S/p.name)
shutil.copytree(BASE/'tests',S/'tests',ignore=shutil.ignore_patterns('__pycache__'))
with zipfile.ZipFile('/tmp/yuanbao-recurrence-stage.zip') as z:
 for name in z.namelist():
  assert name in ('native_core.py','native_client.py','stored_replacements.py','tests/test_stored_replacements.py');z.extract(name,S)
env=os.environ.copy();env['PYTHONDONTWRITEBYTECODE']='1';env['PYTHONPATH']=str(S)+':'+str(S/'tests')+':/home/user/redroid-yuanbao/tools:/home/user/redroid-doubao/geo-batch-code'
test="import socket,requests,sys,unittest; socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('No network in tests')); requests.sessions.Session.request=lambda *a,**k: (_ for _ in ()).throw(AssertionError('No HTTP in tests')); s=unittest.defaultTestLoader.discover(sys.argv[1]); r=unittest.TextTestRunner(verbosity=2).run(s); sys.exit(not r.wasSuccessful())"
r=subprocess.run([sys.executable,'-B','-c',test,str(S/'tests')],env=env,capture_output=True,text=True,timeout=120)
(D/'yuanbao-tests-final.log').write_text(r.stdout+r.stderr);print((r.stdout+r.stderr)[-4500:]);assert r.returncode==0
print(json.dumps({'tests_passed':True,'source_sha256':{n:hashlib.sha256((S/n).read_bytes()).hexdigest() for n in ('native_core.py','native_client.py','stored_replacements.py','tests/test_stored_replacements.py')}}))

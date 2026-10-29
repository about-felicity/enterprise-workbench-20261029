import os,json,zipfile,subprocess
from pathlib import Path
B=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');S=B/'stage-v2';S.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('/tmp/content-compiler22.zip') as z:
 for name in z.namelist():
  p=S/name
  assert S.resolve() in p.resolve().parents
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
env={**os.environ,'PYTHONPATH':str(S)+':'+str(S/'engine')};py='/home/user/geo-editorial/venv/bin/python'
names=json.loads((S/'test-manifest.json').read_text())
for args in ([*['tests.'+n for n in names]],['discover','-s','creation','-t','.', '-p','test_*.py']):
 subprocess.run([py,'-B','-m','unittest',*args],cwd=S,env=env,check=True)
print('CONTENT_UNATTENDED_STAGED_TESTS_PASSED')

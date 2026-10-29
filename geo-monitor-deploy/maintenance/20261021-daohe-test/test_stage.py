import os,sys,json,zipfile,shutil,subprocess,time
from pathlib import Path
B=Path('/opt/monitor/geo-content');S=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic/stage');M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');M.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('/tmp/geo-review-genre-patch.zip') as z:
 names=z.namelist()
 for name in names:
  target=S/name;assert S.resolve() in target.resolve().parents;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
env={**os.environ,'PYTHONPATH':str(S)+':'+str(S/'engine')};py='/home/user/geo-editorial/venv/bin/python'
for args in [['discover','-s','tests','-p','test_*.py'],['discover','-s','creation','-t','.', '-p','test_*.py']]:subprocess.run([py,'-B','-m','unittest',*args],cwd=S,env=env,check=True)
print('STAGED_TESTS_PASSED')

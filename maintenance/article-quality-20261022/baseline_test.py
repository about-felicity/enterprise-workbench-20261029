import os,json,zipfile,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-article-quality');S=D/'baseline-stage';S.mkdir(exist_ok=True)
with zipfile.ZipFile('/tmp/article-quality-baseline.zip') as z:
 for name in z.namelist():
  p=S/name;assert S.resolve() in p.resolve().parents;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
env={**os.environ,'PYTHONPATH':str(S)+':'+str(S/'engine')};py='/home/user/geo-editorial/venv/bin/python'
names=json.loads((S/'test-manifest.json').read_text());results=[]
for label,args in [('engine',['tests.'+n for n in names]),('creation',['discover','-s','creation','-t','.', '-p','test_*.py'])]:
 p=subprocess.run([py,'-B','-m','unittest',*args],cwd=S,env=env,text=True,capture_output=True)
 (D/('baseline-'+label+'-tests.log')).write_text(p.stdout+p.stderr);print(label+': '+p.stderr[-2400:]);results.append({'suite':label,'exit_code':p.returncode})
(D/'baseline-test-results.json').write_text(json.dumps({'at':time.time(),'results':results}));assert all(r['exit_code']==0 for r in results)
import re
html=(S/'creation/panel.html').read_text();js='\n'.join(re.findall(r'<script[^>]*>(.*?)</script>',html,re.S));(D/'panel-check.js').write_text(js)
import shutil
if shutil.which('node'):subprocess.run(['node','--check',str(D/'panel-check.js')],check=True)
else:print('SERVER_NODE_UNAVAILABLE: frontend checked separately on local bundled Node')
print('BASELINE_TESTS_PASSED')

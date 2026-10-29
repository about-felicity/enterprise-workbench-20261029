"""Test final patch and reload at a paid-request boundary; preserve old outputs."""
import os,subprocess,shutil,json,time,zipfile
from pathlib import Path
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic');S=M/'stage'
with zipfile.ZipFile('/tmp/geo-logic-final.zip') as z:
 for name in z.namelist():
  p=S/name;assert S.resolve() in p.resolve().parents
  p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(name))
env={**os.environ,'PYTHONPATH':str(S)+':'+str(S/'engine')};py='/home/user/geo-editorial/venv/bin/python'
subprocess.run([py,'-B','-m','unittest','discover','-s','tests','-p','test_*.py'],cwd=S,env=env,check=True)
subprocess.run([py,'-B','-m','unittest','discover','-s','creation','-t','.', '-p','test_*.py'],cwd=S,env=env,check=True)
for p in (B/'runtime/runs').glob('*/api/active.json'):
 assert json.loads(p.read_text()).get('state') in (None,'SUBMITTED'),'Active paid request '+str(p)
backup=M/('final-backup-'+str(time.time_ns()))
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 for name in ('article_logic.py','consumer_prompts.py','api_worker.py'):
  relative=Path('engine/geo_source_cards')/name;p=B/relative;saved=backup/relative
  saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,saved);shutil.copy2(S/relative,p)
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print('Final logic patch tested and reloaded; original controls and outputs retained')

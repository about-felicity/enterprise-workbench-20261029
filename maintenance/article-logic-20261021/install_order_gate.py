"""Install section-order review and require it for every current delivery root."""
import sys,os,json,time,shutil,subprocess,zipfile
from pathlib import Path
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic');S=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic/stage');M.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile('/tmp/geo-order-patch.zip') as z:
 for name in z.namelist():
  target=S/name;assert S.resolve() in target.resolve().parents
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
env={**os.environ,'PYTHONPATH':str(S)+':'+str(S/'engine')};py='/home/user/geo-editorial/venv/bin/python'
for args in [['discover','-s','tests','-p','test_*.py'],['discover','-s','creation','-t','.', '-p','test_*.py']]:subprocess.run([py,'-B','-m','unittest',*args],cwd=S,env=env,check=True)
for p in (B/'runtime/runs').glob('*/api/active.json'):assert json.loads(p.read_text()).get('state') in (None,'SUBMITTED'),'Active paid request '+str(p)
backup=M/('before-order-gate-'+str(time.time_ns()));backup.mkdir()
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 for name in ['engine/geo_source_cards/article_logic.py','creation/client.py','creation/runtime.py']:
  target=B/name;saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);shutil.copy2(S/name,target)
 roots=[Path('/home/user/geo-editorial/runtime-api')]+[p.parent for p in (B/'runtime/runs').glob('*/job.json')]
 for root in roots:
  target=root/'logic_policy.json';saved=backup/'policies'/root.name;saved.mkdir(parents=True,exist_ok=True)
  if target.exists():shutil.copy2(target,saved/target.name)
  target.write_text(json.dumps({'required':True,'version':'article-logic-v2','reason':'用户要求所有文章检查逻辑和逻辑顺序；未完成复核前不能交付','at':time.time()},ensure_ascii=False))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print('Section-order gate installed for all current roots; prior policies retained')

"""Stage/test logic changes, then deploy only at a verified paid-call boundary."""
import os,json,shutil,subprocess,time,zipfile
from pathlib import Path
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic');stage=M/'stage';stage.mkdir(parents=True,exist_ok=True)
for part,source in [('engine/geo_source_cards',B/'engine/geo_source_cards'),('creation',B/'creation')]:
 shutil.copytree(source,stage/part,dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
with zipfile.ZipFile('/tmp/geo-logic-patch.zip') as z:
 for p in z.namelist():
  target=stage/p;assert stage.resolve() in target.resolve().parents
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(p))
env={**os.environ,'PYTHONPATH':str(stage)+':'+str(stage/'engine')}
python='/home/user/geo-editorial/venv/bin/python'
subprocess.run([python,'-B','-m','unittest','discover','-s',str(stage/'tests'),'-p','test_*.py'],cwd=stage,env=env,check=True)
subprocess.run([python,'-B','-m','unittest','discover','-s','creation','-t','.', '-p','test_*.py'],cwd=stage,env=env,check=True)
for path in (B/'runtime/runs').glob('*/api/active.json'):
 assert json.loads(path.read_text()).get('state') in (None,'SUBMITTED'),'wait for active paid request '+str(path)
backup=M/('backup-'+str(time.time_ns()));backup.mkdir()
engine=['article_logic.py','consumer_voice.py','consumer_prompts.py','api_prompts.py','api_worker.py','daily_editorial.py']
creation=['client.py','runtime.py','quality_repair.py','article_export.py','test_logic_client.py']
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 for part,names in [('engine/geo_source_cards',engine),('creation',creation)]:
  for name in names:
   target=B/part/name;saved=backup/part/name;saved.parent.mkdir(parents=True,exist_ok=True)
   if target.exists():shutil.copy2(target,saved)
   shutil.copy2(stage/part/name,target)
 root=B/'runtime/runs/creation-1792556219-bbc55e13'
 shutil.copytree(root/'approved',M/'original-approved',dirs_exist_ok=True)
 (root/'logic_policy.json').write_text(json.dumps({'required':True,'version':'article-logic-v1','reason':'用户指出全文逻辑严重问题；旧稿保留，复核通过后才恢复下载'}))
 (M/'deployed.json').write_text(json.dumps({'at':time.time(),'backup':str(backup),'no_active_paid_requests':True,'mask_job_control_unchanged':True}))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print('Logic review deployed; original mask outputs retained and held for independent audit')

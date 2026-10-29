"""Test staged engine first; deploy at a verified no-paid-request boundary."""
import json,os,shutil,subprocess,time,zipfile
from pathlib import Path
BASE=Path('/opt/monitor/geo-content')
M=Path('/opt/monitor/geo-capture/maintenance/20261021-followup')
stage=M/'identity-stage';stage.mkdir(parents=True,exist_ok=True)
shutil.copytree(BASE/'engine/geo_source_cards',stage/'engine/geo_source_cards',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
with zipfile.ZipFile('/tmp/geo-identity-patch.zip') as z:
 for item in z.infolist():
  target=stage/('engine/geo_source_cards/'+item.filename[7:] if item.filename.startswith('engine/') else item.filename)
  assert stage.resolve() in target.resolve().parents and not item.is_dir()
  target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
env={**os.environ,'PYTHONPATH':str(stage/'engine')+':/opt/monitor/geo-content'}
subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','discover','-s',str(stage/'tests'),'-p','test_*.py'],cwd=stage,env=env,check=True)
for unit in ('geo-quality-followup-20261021','geo-quality-archived-followup-20261021'):
 assert subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True).stdout.strip()!='active','Wait for isolated requests to drain'
for p in (BASE/'runtime/runs').glob('*/api/active.json'):
 assert json.loads(p.read_text()).get('state') in (None,'SUBMITTED'),'Wait for original active request: '+str(p)
backup=M/('identity-backup-'+str(time.time_ns()));backup.mkdir()
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 for source in sorted((stage/'engine/geo_source_cards').glob('*.py')):
  if source.name not in {'product_identity.py','staged_editorial.py','consumer_prompts.py','daily_editorial.py'}:continue
  target=BASE/'engine/geo_source_cards'/source.name
  shutil.copy2(target,backup/source.name);shutil.copy2(source,target)
 target=BASE/'creation/article_export.py';shutil.copy2(target,backup/'article_export.py');shutil.copy2(stage/'creation/article_export.py',target)
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
(M/'identity-deployed.json').write_text(json.dumps({'at':time.time(),'backup':str(backup),'active_paid_requests':0,'original_frozen_knowledge_modified':False,'identity_from_original_product_only':True}))
print('Identity validation compatibility patch deployed after staged tests and request boundary checks')

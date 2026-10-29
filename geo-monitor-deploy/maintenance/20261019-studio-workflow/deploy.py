"""One-time component-only deployment. Preserve saved plans and all main collectors."""
import base64,hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
root=Path('/opt/monitor/geo-content');maintenance=root/'maintenance/20261019-studio-workflow'
backup=maintenance/('backup-'+str(int(time.time())));backup.mkdir(mode=0o700)
def system(*a):return subprocess.check_output(['systemctl',*a],text=True).strip()
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protected=[Path('/opt/monitor/geo-capture/daily_plan.json'),root/'materials/settings.json',Path('/home/user/geo-editorial/runtime-api/settings.json')]
hashes={str(p):digest(p) for p in protected}
before_jobs=sorted(str(p) for p in (root/'runtime/runs').glob('*/job.json'))
before_plans=sorted(str(p) for p in (root/'studio/plans').glob('*.json'))
main=['geo-deepseek-browser-test.service','geo-native@geo-panel-deepseek2-20261019-103338-38eaf48a.service']
main_pids={s:system('show',s,'-p','MainPID','--value') for s in main}
for p in (root/'runtime/runs').glob('*/api/active.json'):
 active=json.loads(p.read_text());control=json.loads((p.parents[1]/'control.json').read_text())
 assert active.get('state')!='REQUESTING' or control.get('paused'),'Wait for active paid API call; do not interrupt'
services=['geo-creation-studio.service','geo-creation-materials.service','geo-content-worker.service','geo-content-api.service']
active={s:subprocess.run(['systemctl','is-active','--quiet',s]).returncode==0 for s in services}
shutil.copytree(root/'creation',backup/'creation',ignore=shutil.ignore_patterns('__pycache__'))
try:
 for service in services:subprocess.run(['systemctl','stop',service],check=True,timeout=190)
 source=maintenance/'candidate/creation'
 for p in source.iterdir():
  if p.is_file() and p.suffix in {'.py','.html','.md','.js'}:shutil.copy2(p,root/'creation'/p.name)
 sys.path.insert(0,str(root));sys.path.insert(1,str(root/'engine'))
 from creation import studio
 imported=studio.import_word({'filename':'科熙本二硫化硒清爽去屑止痒洗发水知识库.docx','content_base64':base64.b64encode(Path('/tmp/geo-studio-product-knowledge.docx').read_bytes()).decode()})
 assert imported['analysis']['brand']=='科熙本'
 assert before_jobs==sorted(str(p) for p in (root/'runtime/runs').glob('*/job.json'))
 assert before_plans==sorted(str(p) for p in (root/'studio/plans').glob('*.json'))
 assert all(digest(Path(p))==h for p,h in hashes.items())
finally:
 for service in reversed(services):
  if active[service]:subprocess.run(['systemctl','start',service],check=True)
assert all(system('show',s,'-p','MainPID','--value')==pid for s,pid in main_pids.items()),'Main collector PID changed; inspect cause'
receipt={'deployed_at':time.time(),'backup':str(backup),'import_id':imported['import_id'],'product_analysis':{k:imported['analysis'][k] for k in ['name','brand','specification']},'saved_plans_unchanged':True,'paid_jobs_created':0,'main_collector_pids_unchanged':True,'shared_budget_geo_and_0100_settings_unchanged':True,'services':{s:system('is-active',s) for s in services}}
(maintenance/'deployment.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2));print(json.dumps(receipt,ensure_ascii=False))

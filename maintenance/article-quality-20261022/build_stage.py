import hashlib,json,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).parent
engine=['article_compiler.py','argument_plan.py','paragraph_repair.py','api_worker.py','api_prompts.py','consumer_prompts.py','article_logic.py','deepseek_api.py','daily_editorial.py','staged_editorial.py','repair_router.py','editorial_schema.py','section_writer.py','structure_analyzer.py','quality_checks.py','review_quality.py','review_arbitration.py']
old=json.loads((W/'maintenance/content-compiler-20261022/deployment-manifest.json').read_text())['engine_tests']
files={};changed={};before={}
for folder in ('engine','creation'):
 base=W/'source-snapshot/server/opt/monitor/geo-content'/folder
 for p in base.rglob('*'):
  if p.is_file():files[folder+'/'+p.relative_to(base).as_posix()]=p
for n in engine:
 key='engine/geo_source_cards/'+n;local=W/'geo-source-card-collectors/geo_source_cards'/n;prior=files.get(key)
 changed[key]=local;before[key]=hashlib.sha256(prior.read_bytes()).hexdigest() if prior else None
 files[key]=local
for n in ('runtime.py','editorial_status.py','panel.html','test_editorial_health.py'):
 key='creation/'+n;local=W/'geo-monitor-deploy/creation'/n;prior=files.get(key)
 changed[key]=local;before[key]=hashlib.sha256(prior.read_bytes()).hexdigest() if prior else None;files[key]=local
for n in [*old,'test_three_agent_quality']:
 files['tests/'+n+'.py']=W/'geo-source-card-collectors/tests'/(n+'.py')
files['tests/__init__.py']=W/'geo-source-card-collectors/tests/__init__.py'
for p in (W/'geo-monitor-deploy/creation').glob('test_*.py'):files['creation/'+p.name]=p
for key,p in files.items():
 if key.startswith('tests/'):changed[key]=p;before[key]=None
deployed=json.loads((D/'deployed-source.json').read_text()).get('source_files',{}) if (D/'deployed-source.json').exists() else {}
for key in changed:
 before[key]=deployed.get('/opt/monitor/geo-content/'+key,before.get(key))
manifest={'files':{k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in changed.items()},'before':before,'engine_tests':[*old,'test_three_agent_quality']}
(D/'deployment-manifest.json').write_text(json.dumps(manifest,indent=2))
with zipfile.ZipFile(D/'stage.zip','w',zipfile.ZIP_DEFLATED) as z:
 for key,p in files.items():z.writestr(key,p.read_bytes())
 z.writestr('test-manifest.json',json.dumps(manifest['engine_tests']))
print(json.dumps({'files':len(files),'changed':len(changed),'tests':len(manifest['engine_tests'])}))

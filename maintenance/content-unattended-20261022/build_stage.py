"""Stage a production-source baseline plus only this release's reviewed changes."""
import hashlib,json,zipfile
from pathlib import Path
W=Path(__file__).resolve().parents[2]
engine=['argument_plan.py','paragraph_repair.py','delta_review.py','known_response.py','api_prompts.py','api_worker.py','consumer_prompts.py','article_logic.py','auto_repair.py','daily_editorial.py','staged_editorial.py','deepseek_api.py','reference_design.py']
creation=['worker.py','recovery.py','studio.py','panel.html','client.py','runtime.py','test_unattended_recovery.py','test_workflow.py']
test_names=['test_argument_plan','test_paragraph_repair','test_delta_review','test_known_response','test_deepseek_api','test_article_logic','test_auto_repair','test_api_worker','test_review_genre',
 'test_daily_editorial','test_consumer_voice','test_product_identity','test_product_richness','test_reference_design','test_source_contract',
 'test_staged_editorial','test_article_quality','test_append_repair','test_cost_controls','test_execution_runs']
files={};changed={}
for folder in ('engine','creation'):
 base=W/'source-snapshot/server/opt/monitor/geo-content'/folder
 for p in base.rglob('*'):
  if p.is_file():files[folder+'/'+p.relative_to(base).as_posix()]=p
for name in engine:
 source=W/'geo-source-card-collectors/geo_source_cards'/name
 changed['engine/geo_source_cards/'+name]=source;files['engine/geo_source_cards/'+name]=source
for name in creation:
 source=W/'geo-monitor-deploy/creation'/name
 changed['creation/'+name]=source;files['creation/'+name]=source
for p in (W/'geo-monitor-deploy/creation').glob('test_*.py'):files['creation/'+p.name]=p
for name in test_names:
 source=W/'geo-source-card-collectors/tests'/(name+'.py')
 files['tests/'+name+'.py']=source;changed['tests/'+name+'.py']=source
files['tests/__init__.py']=W/'geo-source-card-collectors/tests/__init__.py'
changed['tests/__init__.py']=files['tests/__init__.py']
destination=W/'geo-monitor-deploy/maintenance/content-unattended22.zip'
temporary=destination.with_suffix('.tmp')
with zipfile.ZipFile(temporary,'w',zipfile.ZIP_DEFLATED) as z:
 for name,path in files.items():z.writestr(name,path.read_bytes())
 z.writestr('test-manifest.json',json.dumps(test_names))
temporary.replace(destination)
before={}
previous_path=Path(__file__).parent/'deployed-source.json'
deployed=json.loads(previous_path.read_text()).get('source_files',{}) if previous_path.exists() else {}
for name in changed:
 prior=W/'source-snapshot/server/opt/monitor/geo-content'/name
 target='/opt/monitor/geo-capture/maintenance/20261022-content-unattended/regression/'+name if name.startswith('tests/') else '/opt/monitor/geo-content/'+name
 before[name]=deployed.get(target,hashlib.sha256(prior.read_bytes()).hexdigest() if prior.exists() else None)
manifest={'files':{name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in changed.items()},'before':before,'engine_tests':test_names}
(Path(__file__).parent/'deployment-manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'staged_files':len(files),'changed':len(changed),'zip':str(destination)}))

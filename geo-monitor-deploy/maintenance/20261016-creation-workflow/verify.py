import json,subprocess,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials
R=Path('/opt/monitor/geo-content/maintenance/20261016-creation-workflow')
data=runtime.status();plans=studio.plans();cfg=materials.settings()
assert len(data['jobs'])==2 and sum(len(j['articles']) for j in data['jobs'])+len(data['legacy_articles'])==94
assert len(plans)==1 and not plans[0]['enabled']
assert cfg['enabled'] and cfg['time']=='01:00' and len(cfg['questions'])==16
assert runtime.read(studio.ROOT/'health.json')['status']=='ready'
assert not list((studio.ROOT/'imports').glob('*/source.docx'))
assert not list((studio.ROOT/'days').glob('*/*.json'))
release=runtime.read(R/'release.json')
for name,before in release['jobs_before'].items():
 after=subprocess.check_output(['systemctl','show',name,'--property=MainPID,ActiveEnterTimestampMonotonic'],text=True).strip();assert before==after,(name,before,after)
for name in ['geo-content-api.service','geo-content-worker.service','geo-creation-materials.service','geo-creation-studio.service']:
 assert subprocess.check_output(['systemctl','is-active',name],text=True).strip()=='active'
assert subprocess.check_output(['systemctl','is-enabled','geo-creation-studio.service'],text=True).strip()=='enabled'
result={'approved_articles':94,'preserved_existing_jobs':2,'knowledge_products':len(studio.products()),'migrated_plans':1,'original_capture_time':cfg['time'],'original_capture_questions':len(cfg['questions']),'automatic_paid_writing_enabled':False,'production_test_imports':0,'production_new_daily_runs':0,'scheduler':'ready','collectors_and_creation_worker_unchanged':True}
(R/'verified-runtime.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))

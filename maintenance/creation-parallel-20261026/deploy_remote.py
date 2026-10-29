import hashlib,json,shutil,subprocess,time,os
from pathlib import Path
from creation import parallel,studio
base=Path('/opt/monitor/geo-content/creation');candidate=Path('/tmp/creation-parallel-20261026/creation')
backup=Path('/opt/monitor/geo-content/maintenance/creation-parallel-20261026');(backup/'before').mkdir(parents=True,exist_ok=True)
baseline={'worker.py': '72616aba2442383211623321571c81640490ea3afe817b7dc16626896b286883', 'studio.py': '60cd4c40fdeda635c56ad587f3dd88bd1b551b29f191ac92c568a1ffefbf824c', 'runtime.py': '436ea5f631cba1a3cb668fe4392dd1b89cf379352d01bb437c8b26d79091ee6c', 'panel.html': '0357005f562b9b4955ffaca4a58315a9246706a73cc7be34ff0738c4b880fd9f', 'wizard.js': 'cb04b5a4e86a0eb68906e52dc169e3c47e51d8ffe4942dd9d75f7a0efded38b3', 'wizard_sections.html': 'c4a1bd42c75be080b7be3c58a32526c022325ec9c98403fa2a761ce0baa2e5ca'}
files=['worker.py', 'studio.py', 'runtime.py', 'panel.html', 'wizard.js', 'wizard_sections.html', 'parallel.py', 'test_parallel.py', 'test_studio.py', 'test_worker_recovery.py']
for name,digest in baseline.items():
 assert hashlib.sha256((base/name).read_bytes()).hexdigest()==digest,'production changed: '+name
assert not studio.plans(),'plans changed; reassess running capture'
assert not [p.parent.name for p in (parallel.BASE/'runs').glob('*/job.json') if parallel.eligible(p.parent)],'runnable jobs; drain first'
# No creation browser collector descendants should be active when stopping the old supervisor.
ps=subprocess.check_output(['ps','-eo','args'],text=True)
assert not any('geo_source_cards.cli' in line and '/geo-content/studio/' in line for line in ps.splitlines()),'capture is active'
subprocess.run(['systemctl','stop','geo-content-worker'],check=True,timeout=40)
subprocess.run(['systemctl','kill','--kill-who=all','--signal=SIGTERM','geo-creation-studio'],check=True)
subprocess.run(['systemctl','stop','geo-creation-studio'],check=True,timeout=40)
for name in files:
 target=base/name
 if target.exists():shutil.copy2(target,backup/'before'/name)
 temp=target.with_suffix(target.suffix+'.parallel-tmp');shutil.copy2(candidate/name,temp);os.replace(temp,target)
drop=Path('/etc/systemd/system/geo-content-worker.service.d/parallel.conf');drop.parent.mkdir(parents=True,exist_ok=True)
assert not drop.exists(),'unexpected dropin'
drop.write_text('[Service]\nEnvironment=GEO_CREATION_CONCURRENCY=4\nKillMode=mixed\nTimeoutStopSec=1800\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','restart','geo-content-api','geo-content-worker','geo-creation-studio'],check=True,timeout=40)
time.sleep(3)
for service in ['geo-content-api','geo-content-worker','geo-creation-studio']:
 assert subprocess.check_output(['systemctl','is-active',service],text=True).strip()=='active',service
health=json.loads((parallel.BASE/'worker_health.json').read_text());assert health['mode']=='bounded_processes' and health['max_parallel_jobs']==4 and not health['active_jobs']
result={'files':[{'server':str(base/name),'sha256':hashlib.sha256((base/name).read_bytes()).hexdigest()} for name in files],'health':health,'service_dropin':str(drop),'backup':str(backup),'tests':68,'paid_test_requests':0}
(backup/'release.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

import json,hashlib,os,shutil,subprocess,time,sqlite3
from pathlib import Path
from geo_source_cards.runtime import process_lock,atomic_json
base=Path('/opt/monitor/geo-content/creation');backup=Path('/opt/monitor/geo-content/maintenance/bounded-capture-20261026');(backup/'before').mkdir(exist_ok=True)
baseline={'materials.py': '9cded176115faa7824c0feadbe9026ae896beedb42a2f30d81c010eb3f5169ca', 'studio.py': 'b4e27327ce5acb172507649275c19e565b9afb7e486d7e1aee53bef20b896ce3', 'panel.html': 'b945de87e28a36bc393a1c014e8e18b9ccbc38e84492101db928eaccd0982e14', 'worker.py': 'cdae46ef38f2a6f1cb18cc18be41e6cb35ada603177c501fb90bd09a7047d56e'}
for n,h in baseline.items():assert hashlib.sha256((base/n).read_bytes()).hexdigest()==h,n
root=Path('/opt/monitor/geo-content/studio/capture/plan-29b4419dda224fbd913ae1d9a385497e')
assert not json.loads((root/'health.json').read_text()).get('active_channels'),'capture still draining'
assert json.loads((root/'settings.json').read_text()).get('maintenance_drain')=='bounded-capture-20261026'
for db in (root/'days').glob('*/*/collector/tasks.sqlite'):
 saved=backup/'before'/db.relative_to(root);saved.parent.mkdir(parents=True,exist_ok=True)
 with sqlite3.connect(db) as src,sqlite3.connect(saved) as dst:src.backup(dst)
subprocess.run(['systemctl','kill','--kill-who=all','--signal=SIGTERM','geo-creation-studio'],check=True)
subprocess.run(['systemctl','stop','geo-creation-studio'],check=True,timeout=30)
names=list(baseline)+['search_capture.py','test_bounded_capture.py','test_materials.py']
for n in names:
 if (base/n).exists():shutil.copy2(base/n,backup/'before'/n)
 tmp=base/(n+'.bounded-tmp');shutil.copy2(Path('/tmp/bounded-capture-20261026/creation')/n,tmp);os.replace(tmp,base/n)
with process_lock(root/'settings.lock',blocking=True):
 cfg=json.loads((root/'settings.json').read_text());old=json.loads((backup/'capture-settings-before.json').read_text())
 assert cfg.pop('maintenance_drain',None)=='bounded-capture-20261026'
 cfg['paused']=old.get('paused',False);atomic_json(root/'settings.json',cfg)
subprocess.run(['systemctl','restart','geo-content-api','geo-creation-studio'],check=True,timeout=30)
result={'files':[{'server':str(base/n),'sha256':hashlib.sha256((base/n).read_bytes()).hexdigest()} for n in names],'tests':69,'collector_runtime_test':True,'policy':'3 known read failures per question/channel; keep missing separate; continue usable material; no paid-request retry changes','backup':str(backup)}
(backup/'release.json').write_text(json.dumps(result));print(json.dumps(result))

"""Install memory protection after the existing Doubao2 batch has drained. One-time rollout."""
import json,shutil,sqlite3,subprocess,time
from pathlib import Path
base=Path('/opt/monitor/geo-capture');root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao2-20261020-090001-6bcafb90')
health=json.loads((root/'bridge_health.json').read_text())
assert health['status']=='maintenance_paused' and health['captured']==health['geo_processed'] and not health['delivery_errors']
assert not any(health['tasks'].get(k,0) for k in ('prepared','needs_attention','capturing'))
assert subprocess.run(['systemctl','is-enabled','geo-native@'+root.name+'.service'],capture_output=True,text=True).stdout.strip()=='masked-runtime'
if (root/'maintenance_pause.json').exists():
 marker=json.loads((root/'maintenance_pause.json').read_text());assert marker['source']=='memory_guard_deploy'
# The daily actor may have consumed our drain marker before its masked restart failed.
with sqlite3.connect((base/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True) as control:
 row=control.execute("select desired,batch from daily_tasks where model='doubao2' and day='2026-10-20'").fetchone()
 assert row==('running',root.name),'Do not override a new user pause/configuration'
backup=base/'maintenance/20261020-native-memory';backup.mkdir(parents=True,exist_ok=False,mode=0o700)
db=sqlite3.connect(root/'tasks.sqlite')
with sqlite3.connect(backup/'tasks.before.sqlite') as copy:db.backup(copy)
db.close();(backup/'before-health.json').write_text(json.dumps(health))
mapping={'/tmp/memory-guard-worker.py':Path('/home/user/redroid-doubao/geo-batch-code/question_only_worker.py'),'/tmp/native_memory_guard.py':Path('/home/user/redroid-doubao/geo-batch-code/native_memory_guard.py'),'/tmp/memory-guard-control_panel.py':base/'control_panel.py','/tmp/memory-guard-panel.html':base/'panel.html','/tmp/native_memory_policy.json':base/'native_memory_policy.json'}
for source,target in mapping.items():
 if target.exists():shutil.copy2(target,backup/(target.name+'.before'))
 if target.suffix=='.py':compile(Path(source).read_text(),str(target),'exec')
 if target.name=='native_memory_policy.json':assert not target.exists(),'Never overwrite an existing operator memory policy'
 tmp=target.with_suffix('.memory-new');shutil.copy2(source,tmp);tmp.replace(target)
(backup/'rollout.json').write_text(json.dumps({'at':time.time(),'captured_before':health['captured'],'no_app_restart_at_rollout':True,'policy':json.loads((base/'native_memory_policy.json').read_text())}))
print(json.dumps({'installed':True,'drained_and_processed':health['captured'],'original_queue_preserved':True,'app_not_restarted':True,'backup':str(backup)}))

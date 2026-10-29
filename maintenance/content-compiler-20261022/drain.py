"""Drain all current creation calls before a source reload; preserve user pauses."""
import sys,time,json,hashlib,subprocess
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.pipeline_control import pause,state
from geo_source_cards.runtime import atomic_json
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');file=D/'deployment-drain.json'
if not file.exists() or runtime.read(file).get('restored'):
 rows=[];subprocess.run(['systemctl','stop','geo-creation-studio'],check=True)
 for p in (runtime.BASE/'runs').glob('*/job.json'):
  root=p.parent;old=state(root)
  if old.get('paused'):continue
  paused=pause(root,'source_deploy22','正在收尾当前请求后更新通用创作流程；请求及进度保留')
  rows.append({'job':root.name,'before':old,'pause_revision':paused['revision']})
 atomic_json(file,{'at':time.time(),'paused':rows,'restored':False})
record=runtime.read(file);health=runtime.read(runtime.BASE/'worker_health.json')
safe=health.get('at',0)>record['at'] and all(state(runtime.job_root(r['job'])).get('paused') for r in record['paused'])
print(json.dumps({'drained':safe,'paused_jobs':[r['job'] for r in record['paused']],
                  'worker_heartbeat':health.get('at'),'drain_started':record['at']}))

"""Read-only post-increase checks, including Docker's persisted HostConfig."""
import hashlib,json,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-memory');NAME='yuanbao-hpe14-android13'
run=lambda *args:subprocess.check_output(args,text=True,timeout=20).strip()
x=json.loads(run('docker','inspect',NAME))[0];base=Path(run('docker','info','--format','{{.DockerRootDir}}'))
disk=json.loads((base/'containers'/x['Id']/'hostconfig.json').read_text())
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215');health=json.loads((R/'bridge_health.json').read_text())
sql="select count(*) from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id where e.record->>'batch_id'='"+R.name+"' and r.status='success'"
out={'at':time.time(),'memory_bytes':x['HostConfig']['Memory'],'memory_swap_total_bytes':x['HostConfig']['MemorySwap'],
 'persisted_memory_bytes':disk['Memory'],'persisted_memory_swap_total_bytes':disk['MemorySwap'],
 'app_pid':run('docker','exec',NAME,'pidof','com.tencent.hunyuan.app.chat'),
 'cgroup_memory_max':run('docker','exec',NAME,'cat','/sys/fs/cgroup/memory.max'),
 'cgroup_events':run('docker','exec',NAME,'cat','/sys/fs/cgroup/memory.events'),
 'health':health,'postgres_success':int(run('docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql)),
 'service':run('systemctl','show','geo-native@'+R.name+'.service','-p','ActiveState','--value'),
 'resource_sha256':hashlib.sha256(Path('/home/user/redroid-yuanbao/container_resources.json').read_bytes()).hexdigest()}
assert out['memory_bytes']==out['persisted_memory_bytes']==int(out['cgroup_memory_max'])==4*1024**3
assert out['memory_swap_total_bytes']==out['persisted_memory_swap_total_bytes']==6*1024**3
assert out['app_pid']==json.loads((D/'before.json').read_text())['app_pid']
assert out['cgroup_events']==json.loads((D/'result.json').read_text())['container_oom_events_before']
(D/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))

import json,sys,time,socket,hashlib,subprocess
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
base=Path('/opt/monitor/geo-content/maintenance/task-health-20261030');base.mkdir(parents=True,exist_ok=True)
root=runtime.job_root('creation-1793321691-cba78663');job=runtime.read(root/'job.json')
assert job['date']=='2026-10-30' and job['studio_plan_id']=='plan-f0d530e5eae24fb981e4b191dffeb0ed'
assert job['budget_limits']['task_budget_cny']==6
failure=recovery.http_failure(root)
assert failure and failure['retry_available'] and failure['run_id']=='c83e70a3716393f2e8b6dbcf'
result=runtime.resume(root,allow_http_recovery=True)
runtime.atomic_json(base/'api-recovered.json',{'at':time.time(),'job':job['job_id'],'original_failure':failure,'result':result,'authorization':'REDACTED_CONFIGURE_LOCALLY'})
print('RECOVERY',json.dumps(result),flush=True)
print('RESOLVER',Path('/etc/resolv.conf').read_text(),flush=True)
for host in ['baijiahao.baidu.com','api.deepseek.com','www.sohu.com']:
 for i in range(3):
  started=time.monotonic()
  try:addresses=socket.getaddrinfo(host,443,type=socket.SOCK_STREAM);print('DNS',host,'ok',len(addresses),round(time.monotonic()-started,3),flush=True)
  except OSError as e:print('DNS',host,type(e).__name__,str(e),round(time.monotonic()-started,3),flush=True)
print('MEMORY',subprocess.check_output(['free','-m']).decode())

"""Online RAM increase only; no App restart, question send or task mutation."""
import hashlib,json,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-memory')
NAME='yuanbao-hpe14-android13';PACKAGE='com.tencent.hunyuan.app.chat';G=1024**3
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215')
def command(*args):return subprocess.check_output(args,text=True,timeout=20).strip()
def state():
 x=json.loads(command('docker','inspect',NAME))[0]
 mem={k:int(v.strip().split()[0])*1024 for k,v in (l.split(':',1) for l in Path('/proc/meminfo').read_text().splitlines()) if k in ('MemTotal','MemAvailable','SwapTotal','SwapFree')}
 def value(file):return command('docker','exec',NAME,'cat','/sys/fs/cgroup/'+file)
 return {'at':time.time(),'container_id':x['Id'],'container_pid':x['State']['Pid'],'container_started_at':x['State']['StartedAt'],
  'running':x['State']['Running'],'data_volume':next(m['Name'] for m in x['Mounts'] if m['Destination']=='/data'),
  'memory':x['HostConfig']['Memory'],'memory_swap_total':x['HostConfig']['MemorySwap'],'memory_reservation':x['HostConfig']['MemoryReservation'],
  'app_pid':command('docker','exec',NAME,'pidof',PACKAGE),'host':mem,'cgroup':{f:value(f) for f in ('memory.max','memory.current','memory.events','memory.swap.max','memory.swap.current')},
  'health':json.loads((R/'bridge_health.json').read_text())}
assert not D.exists(),'Preserve previous evidence';D.mkdir(parents=True)
before=state();(D/'before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2))
assert before['running'] and before['data_volume']=='yuanbao-hpe14-android13-data'
assert before['memory']==3*G and before['memory_swap_total']==6*G,'Unexpected existing limits'
assert before['host']['MemAvailable']>=4*G,'Preserve host reserve before increasing one GiB'
assert int(before['cgroup']['memory.swap.current'])<2*G,'Do not squeeze currently allocated swap'
command('docker','update','--memory','4g','--memory-swap','6g',NAME)
after=state();(D/'after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2))
assert after['memory']==4*G and int(after['cgroup']['memory.max'])==4*G
assert after['memory_swap_total']==6*G and int(after['cgroup']['memory.swap.max'])==2*G
assert all(before[k]==after[k] for k in ('container_id','container_pid','container_started_at','data_volume','app_pid')),'Check unexpected process replacement'
config={'container':NAME,'memory_bytes':4*G,'memory_swap_total_bytes':6*G,'swap_allowance_bytes':2*G,
 'effective_at':after['at'],'applied_by':'docker update; persisted in existing container HostConfig',
 'recreate_note':'Recreate only with the existing named data volume and current approved image/command; reapply these limits. Historical provision scripts are not current recovery instructions.'}
p=Path('/home/user/redroid-yuanbao/container_resources.json')
if p.exists():(D/'resources-before.json').write_bytes(p.read_bytes())
tmp=p.with_suffix('.memory23.tmp');tmp.write_text(json.dumps(config,ensure_ascii=False,indent=2));tmp.chmod(0o644);tmp.replace(p)
out={'at':time.time(),'before_memory_bytes':before['memory'],'after_memory_bytes':after['memory'],'total_ram_swap_unchanged':True,
 'container_and_app_not_restarted':True,'questions_resent':0,'task_reset':False,'fees_or_article_api_changed':False,
 'resources_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'before_app_pid':before['app_pid'],'after_app_pid':after['app_pid'],
 'captured':after['health']['captured'],'processed':after['health']['geo_processed'],'container_oom_events_before':before['cgroup']['memory.events'],
 'container_oom_events_after':after['cgroup']['memory.events']}
(D/'result.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))

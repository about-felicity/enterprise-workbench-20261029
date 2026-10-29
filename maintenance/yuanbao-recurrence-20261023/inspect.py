"""Read-only current stalled task/resource/process evidence."""
import hashlib,json,sqlite3,subprocess,time
from pathlib import Path
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215')
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence');D.mkdir(exist_ok=True)
def cmd(*args):
 try:return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=25).strip()
 except Exception as e:return str(e)
read=lambda p:json.loads(p.read_text()) if p.exists() else None
with sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;counts=dict(db.execute('select state,count(*) from tasks group by state'))
 rows=[dict(r) for r in db.execute('select * from tasks where ordinal>=124 and ordinal<=126')]
 for row in rows:
  if row.get('result_json'):row['result_json']={'length':len(row['result_json'])}
  row['events']=[dict(r) for r in db.execute('select * from events where task_id=? order by time desc limit 14',(row['task_id'],))]
  row['files']={p.name:read(p) for p in R.glob(row['task_id']+'.*.json') if p.stat().st_size<40000}
x=json.loads(cmd('docker','inspect','yuanbao-hpe14-android13'))[0]
out={'at':time.time(),'counts':counts,'health':read(R/'bridge_health.json'),'tasks':rows,
 'container':{k:x['State'].get(k) for k in ('Status','OOMKilled','StartedAt','Pid')},'memory_limit':x['HostConfig']['Memory'],
 'memory_events':cmd('docker','exec','yuanbao-hpe14-android13','cat','/sys/fs/cgroup/memory.events'),
 'memory_current':cmd('docker','exec','yuanbao-hpe14-android13','cat','/sys/fs/cgroup/memory.current'),
 'app_pid':cmd('docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat'),
 'app_exit':cmd('docker','exec','yuanbao-hpe14-android13','dumpsys','activity','exit-info','com.tencent.hunyuan.app.chat')[-10000:],
 'foreground':cmd('docker','exec','yuanbao-hpe14-android13','dumpsys','window','windows')[-1500:],
 'host_mem':cmd('free','-m')}
(D/'before.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))

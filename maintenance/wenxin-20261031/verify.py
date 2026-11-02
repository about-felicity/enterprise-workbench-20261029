import hashlib,json,sqlite3,subprocess,time
from pathlib import Path
base=Path('/opt/monitor/geo-capture');work=base/'maintenance/wenxin-20261031';report=json.loads((work/'release.json').read_text())
root=base/'batches'/report['batch']
with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 now={task:hashlib.sha256(value.encode()).hexdigest() for task,value in db.execute("select task_id,result from captures where state='completed'")}
 before=json.loads((work/'completed-before.json').read_text());assert all(now.get(t)==h for t,h in before.items())
 report['completed_now']=len(now)
h=json.loads((root/'bridge_health.json').read_text());report['capture_status']=h.get('status');report['processed_now']=h.get('processed');report['capture_errors']=h.get('errors',[])
p=base/'batches/geo-panel-wenxin-card-20261030-112402-2047183d/collector/verification_probe_latest.json'
if p.exists():
 value=json.loads(p.read_text())
 if value.get('at',0)>time.time()-600:
  report['wenxin_probe']={k:value.get(k) for k in ['at','status','body_length','sources','error']}
print('PROBE_UNIT',subprocess.run(['systemctl','show','geo-wenxin-session-proof-20261031.service','-p','ActiveState','-p','Result','-p','ExecMainStatus'],capture_output=True,text=True).stdout.strip())
print('PROBE_LOG',subprocess.run(['journalctl','-u','geo-wenxin-session-proof-20261031.service','-n','5','--no-pager'],capture_output=True,text=True).stdout[-1800:])
report['files']=[{k:report[k] for k in ['source','server','sha256']}]
assert hashlib.sha256(Path(report['server']).read_bytes()).hexdigest()==report['sha256']
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('VERIFICATION',json.dumps(report,ensure_ascii=False))

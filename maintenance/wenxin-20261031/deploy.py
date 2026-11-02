import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
work=Path('/opt/monitor/geo-capture/maintenance/wenxin-20261031');stage=work/'stage';manifest=json.loads((stage/'manifest.json').read_text());live=Path('/opt/monitor/geo-capture/capture_bridge.py')
assert hashlib.sha256(live.read_bytes()).hexdigest()==manifest['before'],'Production source changed'
assert hashlib.sha256((stage/'capture_bridge.py').read_bytes()).hexdigest()==manifest['sha256']
root=Path('/opt/monitor/geo-capture/batches/geo-panel-baidu-ai-20261031-090001-88a32968');unit='geo-web@'+root.name+'.service'
assert not (root/'pause.json').exists(),'Task was manually paused'
def completed():
 with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:return {task:hashlib.sha256(result.encode()).hexdigest() for task,result in db.execute("select task_id,result from captures where state='completed'")}
before=completed();assert len(before)>=83
(work/'completed-before.json').write_text(json.dumps(before))
shutil.copy2(live,work/'capture_bridge-before.py')
with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as source:
 with sqlite3.connect(work/'tasks-before.sqlite') as dest:source.backup(dest)
temp=live.with_suffix('.py.watchdog.tmp');shutil.copy2(stage/'capture_bridge.py',temp);temp.chmod(0o644);shutil.chown(temp,user='user',group='user');os.replace(temp,live)
try:
 subprocess.run(['systemctl','restart',unit],check=True,timeout=70)
 assert subprocess.check_output(['systemctl','is-active',unit],text=True).strip()=='active'
 after=completed();assert all(after.get(task)==digest for task,digest in before.items()),'Completed results changed'
except Exception:
 shutil.copy2(work/'capture_bridge-before.py',live);subprocess.run(['systemctl','restart',unit],timeout=70);raise
report={'status':'deployed_recovering','tests':18,'before_completed':len(before),'completed_rows_preserved':True,'batch':root.name,'source':'geo-monitor-deploy/capture_bridge.py','server':str(live),'sha256':manifest['sha256']}
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report))

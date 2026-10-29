"""One scoped code reload at a proven unsent boundary; preserve the original batch."""
import json,shutil,sqlite3,subprocess,time
from pathlib import Path
base=Path('/opt/monitor/geo-capture')
lane=next(v for v in json.loads((base/'fleet.json').read_text())['collectors'] if v['name']=='DeepSeek')
root=Path(lane['health']).parent;unit=lane['service']
assert unit.startswith('geo-native@geo-panel-deepseek-app-')
def counts():
 with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  return dict(db.execute('select state,count(*) from tasks group by state'))
before=counts();assert not any(before.get(k,0) for k in ('prepared','needs_attention'))
backup=base/'backups'/('deepseek-greeting-'+str(int(time.time())));backup.mkdir(mode=0o700)
subprocess.run(['systemctl','stop','geo-daily-control.service'],check=True)
try:
 subprocess.run(['systemctl','stop',unit],check=True)
 assert not any(counts().get(k,0) for k in ('prepared','needs_attention'))
 for name in ['device.py','android.py','worker.py']:
  target=Path('/home/user/redroid-deepseek/code')/name
  shutil.copy2(target,backup/name)
  shutil.copy2(Path('/tmp/deepseek-greeting-stage')/name,target)
 assert counts()==before
finally:
 subprocess.run(['systemctl','start',unit],check=True)
 subprocess.run(['systemctl','start','geo-daily-control.service'],check=True)
print(json.dumps({'batch':root.name,'before':before,'after':counts(),'backup':str(backup),'queue_reset':False}))

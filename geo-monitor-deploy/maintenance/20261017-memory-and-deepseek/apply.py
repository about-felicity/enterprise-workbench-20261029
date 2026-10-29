"""Reload only unsent DS preparation and raise API cap without container restart."""
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time

base=Path('/opt/monitor/geo-capture')
backup=base/'backups'/('deepseek-layout-memory-'+str(int(time.time())))
backup.mkdir(mode=0o700)
compose=Path('/opt/monitor/deploy/local-server/docker-compose.yml')
source=compose.read_text()
start=source.index('  dashboard-api:')
end=source.index('\n  ',start+3)
section=source[start:end]
# Next service, not an indented property.
import re
match=re.search(r'\n  [a-zA-Z0-9_-]+:',source[start+3:])
end=start+3+match.start() if match else len(source)
section=source[start:end]
assert section.count('mem_limit: 6g')==1 and section.count('memswap_limit: 7g')==1
shutil.copy2(compose,backup/'docker-compose.yml')
updated=source[:start]+section.replace('mem_limit: 6g','mem_limit: 8g').replace('memswap_limit: 7g','memswap_limit: 9g')+source[end:]
stage=compose.with_suffix('.oom-stage.yml');stage.write_text(updated)
subprocess.run(['docker','compose','-f',str(stage),'config','--quiet'],check=True)
subprocess.run(['docker','update','--memory','8g','--memory-swap','9g','monitor-dashboard-api'],check=True)
stage.replace(compose)

lane=next(v for v in json.loads((base/'fleet.json').read_text())['collectors'] if v['name']=='DeepSeek')
root=Path(lane['health']).parent;unit=lane['service']
assert unit=='geo-native@geo-panel-deepseek-app-20261017-094524.service'
def counts():
 with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  return dict(db.execute('select state,count(*) from tasks group by state'))
before=counts();assert not any(before.get(k,0) for k in ('prepared','needs_attention'))
subprocess.run(['systemctl','stop','geo-daily-control.service'],check=True)
try:
 subprocess.run(['systemctl','stop',unit],check=True)
 assert counts()==before
 target=Path('/home/user/redroid-deepseek/code/android.py')
 shutil.copy2(target,backup/'android.py')
 shutil.copy2('/tmp/deepseek-structural-android-1017.py',target)
 assert counts()==before
finally:
 subprocess.run(['systemctl','start',unit],check=True)
 subprocess.run(['systemctl','start','geo-daily-control.service'],check=True)
print(json.dumps({'backup':str(backup),'before':before,'after':counts(),'queue_reset':False,'api_limit_gib':8}))

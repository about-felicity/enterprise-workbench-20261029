import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
base=Path('/opt/monitor/geo-capture');stamp=str(int(time.time()));backup=base/'backups'/('web-recovery-'+stamp);backup.mkdir(mode=0o700)
package=base/'venv/lib/python3.10/site-packages'
for relative,source in [('web_collectors/collector.py','/tmp/web_collector.fixed.py'),('wenxin_monitor/controller.py','/tmp/wenxin_controller.fixed.py')]:
    target=package/relative;incoming=Path(source);ast.parse(incoming.read_text())
    saved=backup/relative;saved.parent.mkdir(parents=True);shutil.copy2(target,saved)
    temp=target.with_suffix('.fixed');shutil.copy2(incoming,temp);shutil.copymode(target,temp);temp.replace(target)
    # Running Baidu process keeps its loaded code until its next observation.
    # No active collector is stopped or killed for this change.
(backup/'release.json').write_text(json.dumps({'at':time.time(),'scope':'Read navigation timeout origin + single-send coordinate recheck; no prompt changes','active_collectors_restarted':False},indent=2))
print(json.dumps({'backup':str(backup)}))

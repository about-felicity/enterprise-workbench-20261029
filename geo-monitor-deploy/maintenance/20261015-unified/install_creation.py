"""Install independent creation-only API/worker; keep capture and old jobs untouched."""
import json
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

base=Path('/opt/monitor/geo-content');stamp=str(int(time.time()))
backup=Path('/opt/monitor/geo-capture/backups')/('creation-'+stamp);backup.mkdir(mode=0o700)
base.mkdir(mode=0o700,exist_ok=True)
if (base/'creation').exists():shutil.copytree(base/'creation',backup/'creation')
with zipfile.ZipFile('/tmp/geo-creation-runtime.zip') as archive:archive.extractall(base)
engine=base/'engine';engine.mkdir(exist_ok=True)
if not (engine/'geo_source_cards').exists():
    shutil.copytree('/home/user/geo-editorial/venv/lib/python3.10/site-packages/geo_source_cards',engine/'geo_source_cards',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
python='/home/user/geo-editorial/venv/bin/python'
env={'PYTHONPATH':str(base)+':'+str(engine)}
import os
subprocess.run([python,'-B','-m','unittest','creation.test_source_adapter','-v'],env={**os.environ,**env},check=True)
for name,module in [('geo-content-api','service'),('geo-content-worker','worker')]:
    unit=Path('/etc/systemd/system')/(name+'.service')
    if unit.exists():shutil.copy2(unit,backup/unit.name)
    unit.write_text('[Unit]\nDescription=GEO creation-only '+module+'\nAfter=network-online.target docker.service\n[Service]\nType=simple\nWorkingDirectory='+str(base)+'\nEnvironment=PYTHONPATH='+env['PYTHONPATH']+'\nEnvironment=PYTHONDONTWRITEBYTECODE=1\nExecStart='+python+' -B -m creation.'+module+'\nRestart=on-failure\nRestartSec=10\nUMask=0077\nTimeoutStopSec=360\n[Install]\nWantedBy=multi-user.target\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','geo-content-api.service','geo-content-worker.service'],check=True)
(base/'deployment.json').write_text(json.dumps({'installed_at':time.time(),'backup':str(backup),'engine_source':'original installed geo_source_cards snapshot','source':'GEO PostgreSQL + fulltext SQLite','new_platform_collectors':0},indent=2))
print(json.dumps({'installed':True,'backup':str(backup)}))

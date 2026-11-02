import subprocess,json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
print('TIME',datetime.now(ZoneInfo('Asia/Shanghai')).isoformat())
print(subprocess.check_output(['free','-b'],text=True))
print(subprocess.check_output(['docker','stats','--no-stream','--format','{{.Name}} {{.MemUsage}}','monitor-dashboard-api','monitor-product-worker'],text=True))

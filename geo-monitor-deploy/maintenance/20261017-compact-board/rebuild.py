from pathlib import Path
import subprocess
import zipfile
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-compact-board')
zipfile.ZipFile('/tmp/geo-compact-board-source-v2.zip').extractall(ROOT/'stage')
with (ROOT/'build-v2.log').open('w') as log:subprocess.run(['docker','build','-t','monitor-dashboard:compact-board-20261017',str(ROOT)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
subprocess.run(['docker','rm','-f','monitor-dashboard-compact-preview'],check=True)
subprocess.run(['docker','run','-d','--name','monitor-dashboard-compact-preview','--network','host','--memory=512m','monitor-dashboard:compact-board-20261017','npm','run','start','--','-H','127.0.0.1','-p','3001'],check=True)

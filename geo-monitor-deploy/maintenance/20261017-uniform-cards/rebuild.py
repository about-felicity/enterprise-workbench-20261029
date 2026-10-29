from pathlib import Path
import subprocess
import zipfile
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-uniform-cards')
zipfile.ZipFile('/tmp/geo-uniform-cards-source-v2.zip').extractall(ROOT/'stage')
with (ROOT/'build-v2.log').open('w') as log:subprocess.run(['docker','build','-t','monitor-dashboard:uniform-cards-20261017',str(ROOT)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
subprocess.run(['docker','rm','-f','monitor-dashboard-uniform-preview'],check=True)
subprocess.run(['docker','run','-d','--name','monitor-dashboard-uniform-preview','--network','host','--memory=512m','monitor-dashboard:uniform-cards-20261017','npm','run','start','--','-H','127.0.0.1','-p','3001'],check=True)

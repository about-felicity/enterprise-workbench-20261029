import json
from pathlib import Path
import shutil
import subprocess
import zipfile
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-compact-board')
assert all(json.loads((ROOT/('qa-'+m+'.json')).read_text())['passed'] for m in ['preview','production','public'])
zipfile.ZipFile('/tmp/geo-compact-maintenance-final.zip').extractall(ROOT)
shutil.copy2(ROOT/'CURRENT_PROJECT_HANDOFF.md',ROOT.parent/'20261015-unified/CURRENT_PROJECT_HANDOFF.md')
name='monitor-dashboard-compact-preview'
info=json.loads(subprocess.check_output(['docker','inspect',name],text=True))[0]
assert info['Name']=='/'+name and info['Mounts']==[] and info['Config']['Image']=='monitor-dashboard:compact-board-20261017'
subprocess.run(['docker','rm','-f',name],check=True,capture_output=True)
report={'preview_removed':name,'no_data_mounts':True,'source_mappings':json.loads((ROOT.parent/'20261015-unified/current-source-mapping.json').read_text())}
(ROOT/'finalize.json').write_text(json.dumps(report,indent=2))
shutil.copy2(ROOT.parent/'20261015-unified/current-source-mapping.json','/tmp/geo-compact-source-mapping-final.json')
Path('/tmp/geo-compact-source-mapping-final.json').chmod(0o644)
with zipfile.ZipFile('/tmp/geo-compact-evidence-final.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in ROOT.iterdir():
  if p.suffix=='.json' or (p.suffix=='.png' and p.name.startswith('public-')):z.write(p,p.name)
print(json.dumps({'complete':True,'preview_removed':True,'source_matches':report['source_mappings']['matched']}))

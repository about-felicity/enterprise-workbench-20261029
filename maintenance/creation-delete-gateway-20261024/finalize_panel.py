import hashlib,json,os,shutil
from pathlib import Path
D=Path('/tmp/creation-delete-gateway-20261024');P=Path('/opt/monitor/geo-content/maintenance/creation-delete-gateway-20261024/release.json')
assert json.loads((D/'qa-3000.json').read_text())['success']
target=Path('/opt/monitor/geo-content/creation/panel.html');temp=target.with_name('panel.html.installing')
shutil.copy2(D/'stage/panel.html',temp);os.replace(temp,target)
info=json.loads(P.read_text())
for row in info['files']:
 if row['source_name']=='panel.html':row['sha256']=hashlib.sha256(target.read_bytes()).hexdigest()
P.write_text(json.dumps(info,indent=2))

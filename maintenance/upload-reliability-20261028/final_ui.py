import hashlib,json,os,tarfile
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/upload-reliability-20261028');root=Path('/opt/monitor/geo-content/creation')
release=json.loads((base/'release.json').read_text())
with tarfile.open('/tmp/upload-reliability-candidate.tar.gz') as tar:
 for name in ['uploads.js','library.js','panel.html']:
  p=root/name;row=next(r for r in release['files'] if r['server']==str(p))
  assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
  raw=tar.extractfile('creation/'+name).read();tmp=p.with_suffix('.final.tmp');tmp.write_bytes(raw);tmp.chmod(0o644);os.replace(tmp,p);row['sha256']=hashlib.sha256(raw).hexdigest()
for row in release['files']:assert hashlib.sha256(Path(row['server']).read_bytes()).hexdigest()==row['sha256']
(base/'release.json').write_text(json.dumps(release,indent=2));print('12 deployed file hashes verified; upload wait 600 seconds')

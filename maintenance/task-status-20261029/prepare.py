import json,hashlib,tarfile,difflib
from pathlib import Path
w=Path(__file__).resolve().parents[2];d=Path(__file__).parent
expected={}
with tarfile.open(d/'candidate.tar.gz','w:gz') as tar:
 for n in ['studio.py','panel.html']:
  old=(d/'before'/n).read_bytes();new=(w/'geo-monitor-deploy/creation'/n).read_bytes();expected[n]=hashlib.sha256(old).hexdigest()
  diff=''.join(difflib.unified_diff(old.decode().splitlines(True),new.decode().splitlines(True),fromfile='before/'+n,tofile='after/'+n))
  (d/(n+'.diff')).write_text(diff,encoding='utf8');tar.add(w/'geo-monitor-deploy/creation'/n,arcname=n)
  if n.endswith('.py'):compile(new,n,'exec');print(diff)
 (d/'expected.json').write_text(json.dumps(expected));tar.add(d/'expected.json',arcname='expected.json')

import zipfile,json,hashlib
from pathlib import Path
w=Path('maintenance/doubao-expand-20261102')
with zipfile.ZipFile(w/'lanes.zip') as z:
 m=json.loads(z.read('manifest.json'));a='redroid-deploy/question_only_adapters.py';p=Path(a);orig=Path('source-snapshot/server/home/user/redroid-doubao/geo-batch-code/question_only_adapters.py').read_bytes()
 assert p.read_bytes()==z.read(a) and hashlib.sha256(orig.replace(b'\r\n',b'\n')).hexdigest()==m[a]['base']
 p.write_bytes(orig);m.pop(a)
 with zipfile.ZipFile(w/'strict-lanes.zip','w',zipfile.ZIP_DEFLATED) as out:
  for name in m:out.writestr(name,z.read(name))
  out.writestr('manifest.json',json.dumps(m))

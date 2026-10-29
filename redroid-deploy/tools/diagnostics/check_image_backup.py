
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import tarfile,json,pathlib,hashlib
p=pathlib.Path('/home/user/redroid-doubao/backups/hpe14-20261006/redroid13-hpe14-image.tar')
with tarfile.open(p) as t:
 m=json.load(t.extractfile('manifest.json'));print(m)
 for e in m:
  c=t.extractfile(e['Config']).read();print('configsha',hashlib.sha256(c).hexdigest());j=json.loads(c);print({k:j.get(k) for k in ['created','architecture','os','rootfs']});print('history-last',j.get('history',[])[-1:])

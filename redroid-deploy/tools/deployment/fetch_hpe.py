
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import requests,pathlib,hashlib,tarfile,io,json
ref='2f8f088671182e17e67321e098e8411a3972a628'
r=requests.get('https://codeload.github.com/supremegamers/vendor_intel_proprietary_houdini/tar.gz/'+ref,timeout=120);r.raise_for_status()
p=pathlib.Path('redroid-deploy/artifacts/houdini-hpe14.tar.gz');p.write_bytes(r.content)
print('Downloaded',len(r.content),hashlib.sha256(r.content).hexdigest())
with tarfile.open(p) as t:
 for m in t.getmembers():
  if any(v in m.name for v in ['linker','libhoudini.so','cpuinfo','houdini64']): print(m.name,m.size)

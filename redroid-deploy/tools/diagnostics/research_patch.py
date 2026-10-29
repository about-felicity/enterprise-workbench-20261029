
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import requests,json,pathlib
base='https://api.github.com/repos/supremegamers/vendor_intel_proprietary_houdini'
for suffix in ['/pulls/7','/pulls/7/files','/branches?per_page=100']:
 r=requests.get(base+suffix,timeout=30); j=r.json(); print(suffix)
 if isinstance(j,list):
  for x in j: print({k:x.get(k) for k in ['name','filename','status','raw_url','patch']})
 else: print({k:j.get(k) for k in ['state','merged','merge_commit_sha','body','head','base']})
r=requests.get('https://api.github.com/repos/Vvamp/Libhoudini-hpe-14-timebomb-patch/contents',timeout=30)
for x in r.json(): print(x.get('name'),x.get('download_url'))

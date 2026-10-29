
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import requests
for repo in ['supremegamers/vendor_intel_proprietary_houdini','casualsnek/waydroid_script','waydroid/waydroid']:
 r=requests.get(f'https://api.github.com/repos/{repo}/issues?state=all&per_page=100',timeout=30)
 print(repo,r.status_code)
 if r.ok:
  for x in r.json():
   t=x['title']; b=x.get('body') or ''
   if any(v in (t+' '+b).lower() for v in ['september','expiration','expire','timebomb','time bomb','2026-09','houdini stops']): print(x['number'],t,x['html_url'],b[:5000])

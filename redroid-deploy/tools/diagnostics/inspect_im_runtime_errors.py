
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,re
name='doubao-hpe14-account2'
raw=subprocess.check_output(['docker','exec',name,'logcat','-d','-v','brief','-t','15000'],text=True,errors='replace')
for line in raw.splitlines():
    if re.search(r'sqlite|omni|conversation|database|im_sdk|flowim|disk full',line,re.I) and re.search(r'fail|error|exception|invalid|abort|denied',line,re.I):
        if not re.search(r'token|cookie|authorization|ticket|https?://',line,re.I):
            print(re.sub(r'\d{8,}','[id]',line)[:600])

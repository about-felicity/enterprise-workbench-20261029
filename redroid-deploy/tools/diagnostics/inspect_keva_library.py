
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import zipfile,re,subprocess
from pathlib import Path
apk=Path('/home/user/redroid-doubao/account2/doubao-15.2.0.apk')
with zipfile.ZipFile(apk) as z:
    for n in z.namelist():
        if n.endswith('.so') and ('keva' in n.lower()):
            data=z.read(n);print('library',n,len(data))
            dest=Path('/home/user/redroid-doubao/account2')/Path(n).name;dest.write_bytes(data)
            for s in re.findall(rb'[ -~]{4,}',data):
                if any(x in s for x in (b'.blk',b'.chk',b'%s/',b'snprintf')):print(s.decode()[:400])

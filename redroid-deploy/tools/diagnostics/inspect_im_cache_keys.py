
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json,subprocess,re
from pathlib import Path
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/files/keva/repo'
    for dirname in ('FlowIMSDKomni_im_default_repo','FlowIMSDK'):
        keys=set()
        for p in (root/dirname).glob('*.blk'):
            for raw in re.findall(rb'[ -~]{5,160}',p.read_bytes()):
                s=raw.decode()
                if re.search('cursor|sync|version|init|pull|conversation|db_',s,re.I) and not re.search('token|ticket|session|auth',s,re.I):
                    keys.add(re.sub(r'\d{8,}','[id]',s))
        print(name,dirname,sorted(keys))

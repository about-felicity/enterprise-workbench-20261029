
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json,subprocess,re
from pathlib import Path
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/files'
    for filename in ('hostcache_v1','hostcache_sync_v1','tt_net_config.config','server.json'):
        p=root/filename
        try:
            raw=p.read_bytes()
            v=json.loads(raw)
            print(name,filename,'keys',list(v)[:35] if isinstance(v,dict) else type(v).__name__)
            if filename=='server.json':
                data=v.get('data',{})
                print('data_keys',list(data)[:80] if isinstance(data,dict) else type(data).__name__)
        except OSError: print(name,filename,'unavailable')
        except ValueError:
            print(name,filename,'header',raw[:16].hex(),'length',len(raw))
            print('hosts',sorted(set(x.decode() for x in re.findall(rb'[A-Za-z0-9][A-Za-z0-9.-]+\.(?:com|cn|net|org)\b',raw))))

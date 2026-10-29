
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,re
from pathlib import Path
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))
    pid=subprocess.check_output(['docker','exec',name,'pidof','com.larus.nova'],text=True).strip()
    fds=subprocess.check_output(['docker','exec',name,'ls','-l','/proc/'+pid+'/fd'],text=True)
    print(name)
    for line in fds.splitlines():
        if 'conversation-local-manager' in line:
            path=line.split(' -> ')[-1]
            print('fd',line.split(' -> ')[0].split()[-1],'path_length',len(path),'basename_length',len(Path(path).name),'suffix',path[-15:])
    for d in (root/'data/com.larus.nova/files/keva/repo').glob('FlowIMSDKconversation-local-manager*'):
        print('directory_length',len(d.name),'files',[(len(p.name),p.name[-12:],p.stat().st_ino,p.stat().st_size) for p in d.iterdir()])

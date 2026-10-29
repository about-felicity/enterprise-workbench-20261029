
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,sqlite3,json,subprocess,re
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import databases
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    print(name)
    for p in databases(name):
        c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
        tables=[r[0] for r in c.execute("select name from sqlite_master where type='table'")]
        print('db',p.name[:19]+'...'+p.name[-6:],'counts',[(t,c.execute('select count(*) from '+t).fetchone()[0]) for t in tables if t in ('im_conversation','im_message')])
    info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/files/keva/repo'
    for p in root.iterdir():
        if re.search('im|conversation',p.name,re.I):
            print('cache',re.sub(r'\d{8,}','[id]',p.name), 'files',[(x.name,x.stat().st_size) for x in p.iterdir()][:20] if p.is_dir() else p.stat().st_size)

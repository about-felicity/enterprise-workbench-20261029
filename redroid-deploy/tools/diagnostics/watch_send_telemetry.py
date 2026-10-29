
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,sqlite3,re,time
from pathlib import Path
info=json.loads(subprocess.check_output(['docker','inspect','doubao-hpe14-account2']))[0]
root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/databases'
c=sqlite3.connect((root/'482431@bd_tea_agent.db').resolve().as_uri()+'?mode=ro',uri=True)
seen=set(); end=time.monotonic()+45
while time.monotonic()<end:
    for table in ('eventv3','forward_eventv3'):
        for ident,event,params in c.execute('select _id,event,params from '+table+' order by _id desc limit 100'):
            if (table,ident) in seen:continue
            seen.add((table,ident))
            if not re.search('send|im_|chat|request|network|connect',event or '',re.I):continue
            try:v=json.loads(params or '{}')
            except ValueError:continue
            fields={k:v for k,v in v.items() if re.fullmatch(r'(?:error|err|status|result|fail|success|duration|cost|http|network|cmd|command|path|api|method|msg|sdk|init)[\w_]*',k,re.I) and not re.search('text|body|content|token|cookie|session|message|id',k,re.I)}
            if event not in ('flow_im_network_shortlink_request',):
                print(json.dumps({'event':event,'keys':list(v),'fields':fields},ensure_ascii=False),flush=True)
    time.sleep(.2)
print('Telemetry observation complete; rows seen',len(seen),flush=True)

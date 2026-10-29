
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import sys,sqlite3,json,re,subprocess
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import databases
for p in databases('doubao-hpe14-account2'):
    c=sqlite3.connect(p.resolve().as_uri()+'?mode=ro',uri=True)
    for row in c.execute('select ext,biz_extra from im_message where user_type=1 order by rowid desc limit 2'):
        for raw in row:
            try: value=json.loads(raw or '{}')
            except ValueError: continue
            if isinstance(value,dict):
                print('message_metadata_keys',list(value))
                print('error_fields',{k:v for k,v in value.items() if re.search('error|status|code|reason',k,re.I)})
info=json.loads(subprocess.check_output(['docker','inspect','doubao-hpe14-account2']))[0]
mount=next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data')
app=Path(mount)/'data/com.larus.nova'
logs=sorted((app/'files/logs').glob('*__default.alog.hot'),key=lambda p:p.stat().st_mtime)[-2:]
for p in logs:
    raw=p.read_bytes()
    print('log_format',len(raw),raw[:24].hex())
    strings=re.findall(rb'[ -~]{12,}',raw)
    print('printable_segments',len(strings))
    for s in strings:
        line=s.decode()
        if re.search(r'(?i)(send.*fail|error_code|status_code|connect.*fail)',line) and not re.search('(?i)token|cookie|key|session',line):
            print(re.sub(r'https?://\S+','[URL]',line)[:300])
db=app/'databases/apm_monitor_t1.db'
c=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
print('apm_tables',[r[0] for r in c.execute("select name from sqlite_master where type='table'")])
tea=app/'databases/482431@bd_tea_agent.db'
c=sqlite3.connect(tea.resolve().as_uri()+'?mode=ro',uri=True)
for table,sql in c.execute("select name,sql from sqlite_master where type='table'"):
    pass
for event,raw in c.execute('select event,params from eventv3 order by _id desc limit 100'):
    try: value=json.loads(raw or '{}')
    except ValueError: continue
    print('telemetry_event',event,{k:v for k,v in value.items() if re.search(r'error|status|code|reason|success|result|duration',k,re.I) and not re.search(r'body|content|text|token|key|cookie|session',k,re.I)})

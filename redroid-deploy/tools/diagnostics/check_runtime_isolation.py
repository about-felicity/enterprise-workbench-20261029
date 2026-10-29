"""Read-only process, namespace, storage and session isolation audit."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,sqlite3,hashlib,collections,re
from pathlib import Path
def run(*args):return subprocess.check_output(args,text=True,errors='replace',timeout=15).strip()
seen=[]
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    info=json.loads(run('docker','inspect',name))[0]
    root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))
    pid=run('docker','exec',name,'pidof','com.larus.nova')
    process=run('docker','exec',name,'ps','-T','-p',pid,'-o','PID,TID,STAT,WCHAN,NAME')
    counts=collections.Counter()
    blocked=[]
    for line in process.splitlines()[1:]:
        parts=line.split()
        if len(parts)>=5:
            counts[parts[2]]+=1
            if parts[2].startswith('D'):blocked.append(line)
    record={'container':name,'host_init_pid':info['State']['Pid'],'app_android_pid':pid,'volume':str(root),
            'network_namespace':run('readlink','/proc/'+str(info['State']['Pid'])+'/ns/net'),
            'pid_namespace':run('readlink','/proc/'+str(info['State']['Pid'])+'/ns/pid'),
            'thread_states':dict(counts),'kernel_blocked_threads':blocked}
    print(json.dumps(record));seen.append(record)
    app=root/'data/com.larus.nova'
    db=app/'databases/account_db'
    c=sqlite3.connect(db.resolve().as_uri()+'?mode=ro',uri=True)
    print(name,'account_schema',list(c.execute("select name,sql from sqlite_master where type='table'")))
    print(name,'session_related_pref_filenames',[p.name for p in (app/'shared_prefs').glob('*.xml') if re.search('account|passport|session|cookie',p.name,re.I)])
print('isolation',{'separate_data_volumes':seen[0]['volume']!=seen[1]['volume'],'separate_network_namespaces':seen[0]['network_namespace']!=seen[1]['network_namespace'],'separate_pid_namespaces':seen[0]['pid_namespace']!=seen[1]['pid_namespace']})
for service in ('redroid-geo-products.service','redroid-geo-products-account2.service'):
    print(service,run('systemctl','show',service,'-p','ActiveState','-p','SubState','-p','MainPID'))

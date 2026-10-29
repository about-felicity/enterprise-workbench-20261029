"""Probe public chat host TLS reachability without credentials or chat payloads."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,json,re,socket,ssl,concurrent.futures
from pathlib import Path
hosts=set()
for name in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
    info=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
    root=Path(next(m['Source'] for m in info['Mounts'] if m['Destination']=='/data'))/'data/com.larus.nova/files'
    raw=(root/'hostcache_sync_v1').read_text(errors='replace')
    for line in raw.splitlines():
        found=re.search(r'[A-Za-z0-9.-]+\.doubao\.com',line)
        if found:
            host=found.group(); hosts.add(host)
            print(name,host,'cache_ips',re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b',line))
def probe(host):
    try:
        addresses=sorted(set(r[4][0] for r in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM)))
        with socket.create_connection((host,443),timeout=5) as conn:
            with ssl.create_default_context().wrap_socket(conn,server_hostname=host) as tls:
                return {'host':host,'addresses':addresses,'tls':'ok','peer':tls.getpeername()[0]}
    except Exception as exc:return {'host':host,'error':type(exc).__name__+': '+str(exc)}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    for result in pool.map(probe,sorted(hosts)): print(json.dumps(result))
